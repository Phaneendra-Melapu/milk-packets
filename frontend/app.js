const packetButtons = document.querySelector("#packetButtons");
const packetTemplate = document.querySelector("#packetTemplate");
const cartItems = document.querySelector("#cartItems");
const historyList = document.querySelector("#historyList");
const purchaseDate = document.querySelector("#purchaseDate");
const totalPackets = document.querySelector("#totalPackets");
const dailyTotal = document.querySelector("#dailyTotal");
const averagePrice = document.querySelector("#averagePrice");
const cartDateLabel = document.querySelector("#cartDateLabel");

let selectedDate = new Date().toISOString().slice(0, 10);
let dayData = { date: selectedDate, items: [], packetCount: 0, total: 0 };

function money(value) {
  return `Rs ${Number(value).toLocaleString("en-IN")}`;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong");
  }

  return data;
}

function createPacketArt(packet) {
  if (packet.imageUrl) {
    return `<img src="${packet.imageUrl}?v=${Date.now()}" alt="${packet.name} packet" />`;
  }

  return `
    <span class="packet-placeholder" style="--packet-color: ${packet.color}">
      <span>${packet.name}</span>
      <small>Milk</small>
    </span>
  `;
}

function renderPackets() {
  packetButtons.replaceChildren();

  dayData.items.forEach((packet) => {
    const node = packetTemplate.content.firstElementChild.cloneNode(true);
    const button = node.querySelector(".packet-button");
    const image = node.querySelector(".packet-image");
    const name = node.querySelector(".packet-name");
    const price = node.querySelector(".packet-price");
    const upload = node.querySelector(".image-upload");
    const locked = node.querySelector(".image-locked");
    const input = node.querySelector("input");

    node.style.setProperty("--accent", packet.color);
    button.dataset.packetId = packet.id;
    image.innerHTML = createPacketArt(packet);
    name.textContent = packet.name;
    price.textContent = `${money(packet.price)} each`;
    upload.hidden = Boolean(packet.imageUrl);
    locked.hidden = !packet.imageUrl;

    button.addEventListener("click", () => addPacket(packet.id));
    input.addEventListener("change", (event) => uploadImage(packet.id, event.target.files[0]));

    packetButtons.append(node);
  });
}

function renderCart() {
  const activeItems = dayData.items.filter((item) => item.quantity > 0);
  cartItems.replaceChildren();
  cartDateLabel.textContent = new Date(`${dayData.date}T00:00:00`).toLocaleDateString("en-IN", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  if (activeItems.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No packets added for this date.";
    cartItems.append(empty);
    return;
  }

  activeItems.forEach((item) => {
    const row = document.createElement("article");
    row.className = "cart-row";
    row.innerHTML = `
      <span class="cart-dot" style="background: ${item.color}"></span>
      <div>
        <strong>${item.name}</strong>
        <span>${item.quantity} x ${money(item.price)}</span>
      </div>
      <div class="stepper">
        <button type="button" aria-label="Remove ${item.name}">-</button>
        <input type="number" min="0" value="${item.quantity}" aria-label="${item.name} quantity" />
        <button type="button" aria-label="Add ${item.name}">+</button>
      </div>
      <strong>${money(item.subtotal)}</strong>
    `;

    const [minusButton, plusButton] = row.querySelectorAll("button");
    const quantityInput = row.querySelector("input");
    minusButton.addEventListener("click", () => removePacket(item.id));
    plusButton.addEventListener("click", () => addPacket(item.id));
    quantityInput.addEventListener("change", () => setPacket(item.id, quantityInput.value));

    cartItems.append(row);
  });
}

function renderTotals() {
  totalPackets.textContent = dayData.packetCount;
  dailyTotal.textContent = money(dayData.total);
  averagePrice.textContent = dayData.packetCount ? money(Math.round(dayData.total / dayData.packetCount)) : "Rs 0";
}

function renderHistory(days) {
  historyList.replaceChildren();

  if (days.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "Your saved days will appear here.";
    historyList.append(empty);
    return;
  }

  days.forEach((day) => {
    const button = document.createElement("button");
    button.className = "history-day";
    button.type = "button";
    button.innerHTML = `
      <span>${new Date(`${day.date}T00:00:00`).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
      })}</span>
      <strong>${money(day.total)}</strong>
      <small>${day.packetCount} packets</small>
    `;
    button.addEventListener("click", () => {
      selectedDate = day.date;
      purchaseDate.value = selectedDate;
      loadDay();
    });
    historyList.append(button);
  });
}

function render() {
  renderTotals();
  renderPackets();
  renderCart();
}

async function loadDay() {
  dayData = await requestJson(`/api/milk/day?purchase_date=${selectedDate}`);
  render();
  loadHistory();
}

async function loadHistory() {
  const data = await requestJson("/api/milk/history?limit=14");
  renderHistory(data.days);
}

async function addPacket(packetId) {
  dayData = await requestJson(`/api/milk/day/${selectedDate}/${packetId}/add`, { method: "POST" });
  render();
  loadHistory();
}

async function removePacket(packetId) {
  dayData = await requestJson(`/api/milk/day/${selectedDate}/${packetId}/remove`, { method: "POST" });
  render();
  loadHistory();
}

async function setPacket(packetId, quantity) {
  const safeQuantity = Math.max(0, Number.parseInt(quantity, 10) || 0);
  dayData = await requestJson(`/api/milk/day/${selectedDate}/${packetId}/${safeQuantity}`, { method: "PUT" });
  render();
  loadHistory();
}

async function uploadImage(packetId, file) {
  if (!file) return;

  const formData = new FormData();
  formData.append("image", file);
  await fetch(`/api/milk/packets/${packetId}/image`, {
    method: "POST",
    body: formData,
  });
  await loadDay();
}

purchaseDate.value = selectedDate;
purchaseDate.addEventListener("change", () => {
  selectedDate = purchaseDate.value || new Date().toISOString().slice(0, 10);
  loadDay();
});

loadDay();
