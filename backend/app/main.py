from pathlib import Path

from datetime import date

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError

from .agent_logger import read_agent_logs
from .auth import create_access_token, decode_access_token, hash_password, verify_password
from .database import (
    add_milk_packet,
    create_tables,
    create_user,
    get_daily_purchases,
    get_packet_image,
    get_user_by_email,
    list_milk_packets,
    read_purchase_history,
    set_milk_packet_quantity,
    update_packet_image,
)
from .schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from .simple_agents import run_basic_agent_workflow
from .qa_runner import run_playwright_tests
from .structured_agents import run_structured_workflow


app = FastAPI(title="Multi-Agent Login System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.on_event("startup")
def on_startup() -> None:
    create_tables()


def row_to_user(row) -> UserResponse:
    return UserResponse(id=row["id"], name=row["name"], email=row["email"])


def get_current_user(authorization: str = Header(default="")) -> UserResponse:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    email = decode_access_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )
    return row_to_user(user)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "sw.js", media_type="application/javascript")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def milk_row_to_dict(row) -> dict:
    quantity = int(row["quantity"])
    price = int(row["price"])
    return {
        "id": row["id"],
        "name": row["name"],
        "price": price,
        "color": row["color"],
        "imageUrl": f"/api/milk/packets/{row['id']}/image" if row["has_image"] else None,
        "quantity": quantity,
        "subtotal": quantity * price,
    }


def build_daily_summary(purchase_date: str) -> dict:
    items = [milk_row_to_dict(row) for row in get_daily_purchases(purchase_date)]
    return {
        "date": purchase_date,
        "items": items,
        "packetCount": sum(item["quantity"] for item in items),
        "total": sum(item["subtotal"] for item in items),
    }


@app.get("/api/milk/packets")
def milk_packets() -> dict:
    packets = []
    for row in list_milk_packets():
        packets.append(
            {
                "id": row["id"],
                "name": row["name"],
                "price": int(row["price"]),
                "color": row["color"],
                "imageUrl": f"/api/milk/packets/{row['id']}/image" if row["has_image"] else None,
            }
        )
    return {"packets": packets}


@app.get("/api/milk/day")
def milk_day(purchase_date: str | None = None) -> dict:
    return build_daily_summary(purchase_date or date.today().isoformat())


@app.post("/api/milk/day/{purchase_date}/{packet_id}/add")
def add_packet_to_day(purchase_date: str, packet_id: str) -> dict:
    add_milk_packet(packet_id=packet_id, purchase_date=purchase_date, amount=1)
    return build_daily_summary(purchase_date)


@app.post("/api/milk/day/{purchase_date}/{packet_id}/remove")
def remove_packet_from_day(purchase_date: str, packet_id: str) -> dict:
    add_milk_packet(packet_id=packet_id, purchase_date=purchase_date, amount=-1)
    return build_daily_summary(purchase_date)


@app.put("/api/milk/day/{purchase_date}/{packet_id}/{quantity}")
def set_packet_count(purchase_date: str, packet_id: str, quantity: int) -> dict:
    set_milk_packet_quantity(packet_id=packet_id, purchase_date=purchase_date, quantity=quantity)
    return build_daily_summary(purchase_date)


@app.post("/api/milk/packets/{packet_id}/image")
def upload_packet_image(packet_id: str, image: UploadFile = File(...)) -> dict:
    if image.content_type is None or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an image file.",
        )

    image_bytes = image.file.read()
    if len(image_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload an image smaller than 5 MB.",
        )

    if not update_packet_image(packet_id, image_bytes, image.content_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown milk packet type.",
        )

    return {"packetId": packet_id, "imageUrl": f"/api/milk/packets/{packet_id}/image"}


@app.get("/api/milk/packets/{packet_id}/image")
def read_packet_image(packet_id: str) -> Response:
    image = get_packet_image(packet_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Packet image is not uploaded yet.",
        )
    return Response(content=image["image_data"], media_type=image["image_mime"])


@app.get("/api/milk/history")
def milk_history(limit: int = 14) -> dict:
    rows = read_purchase_history(limit=max(1, min(limit, 60)))
    return {
        "days": [
            {
                "date": row["purchase_date"],
                "packetCount": int(row["packets"] or 0),
                "total": int(row["total"] or 0),
            }
            for row in rows
        ]
    }


@app.get("/api/agents/run")
def run_agents_demo(run_tests: bool = False) -> dict:
    return run_structured_workflow(
        user_input="Build a secure user registration and login system.",
        run_tests=run_tests,
    )


@app.get("/api/basic-agents/run")
def run_basic_agents_demo() -> dict:
    result = run_basic_agent_workflow(
        user_input="I want a simple user registration and login system."
    )
    return {
        "status": "finished",
        "workflow": [
            "User Input",
            "Product Manager Agent",
            "Business Analyst Agent",
            "Developer Agent",
            "QA Agent",
        ],
        "result": result,
    }


@app.get("/api/structured-agents/run")
def run_structured_agents_demo(run_tests: bool = False) -> dict:
    result = run_structured_workflow(
        user_input="Build a secure user registration and login system.",
        run_tests=run_tests,
    )
    return result


@app.get("/api/agents/logs")
def read_recent_agent_logs(limit: int = 50) -> dict:
    return {
        "status": "success",
        "logs": read_agent_logs(limit=limit),
    }


@app.post("/api/qa/run-playwright")
def run_qa_playwright_tests() -> dict:
    result = run_playwright_tests()
    return result.to_dict()


@app.post("/api/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest) -> TokenResponse:
    try:
        user = create_user(
            name=payload.name.strip(),
            email=str(payload.email),
            hashed_password=hash_password(payload.password),
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        ) from None

    user_response = row_to_user(user)
    token = create_access_token(subject=user_response.email)
    return TokenResponse(access_token=token, user=user_response)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = get_user_by_email(str(payload.email))
    if user is None or not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user_response = row_to_user(user)
    token = create_access_token(subject=user_response.email)
    return TokenResponse(access_token=token, user=user_response)


@app.get("/api/auth/me", response_model=UserResponse)
def read_current_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
