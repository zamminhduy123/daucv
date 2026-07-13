import jwt
from fastapi import Depends, Header, HTTPException

from app.core.config import NEXTAUTH_SECRET
from app.core.db import Database


async def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing authorization header.",
        )

    token = authorization.split(" ")[1]
    try:
        # Decode the NextAuth JWT signed via HS256
        payload = jwt.decode(token, NEXTAUTH_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Unauthorized: Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token.")

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=401, detail="Unauthorized: Token missing email."
        )

    # Fetch user from Database
    user = await Database.fetch_one(
        "SELECT id, email, name, image, credits FROM public.users WHERE email = $1",
        email,
    )
    if not user:
        # Fallback registration if not synchronised yet
        name = payload.get("name", email.split("@")[0])
        image = payload.get("picture") or payload.get("image")

        try:
            await Database.execute(
                "INSERT INTO public.users (email, name, image, credits) VALUES ($1, $2, $3, 20) ON CONFLICT (email) DO NOTHING",
                email,
                name,
                image,
            )
            user = await Database.fetch_one(
                "SELECT id, email, name, image, credits FROM public.users WHERE email = $1",
                email,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Database synchronization error: {e}"
            )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: User profile could not be created or fetched.",
            )

    return dict(user)


def verify_credits(required_credits: int = 1):
    async def _verify(user: dict = Depends(get_current_user)):
        if user["credits"] < required_credits:
            raise HTTPException(
                status_code=403,
                detail=f"Hết lượt sử dụng (Credits)! Yêu cầu tối thiểu {required_credits} credit. Vui lòng nạp thêm credit để tiếp tục.",
            )
        return user

    return _verify


async def deduct_credits(user_id, amount: int, tx_type: str, description: str) -> int:
    """
    Transactionally deducts credits from a user profile and logs a transaction ledger record.
    Returns the new credit balance.
    """
    if amount >= 0:
        raise ValueError("Deduction amount must be negative.")

    if not Database.pool:
        await Database.connect()

    async with Database.pool.acquire() as conn, conn.transaction():
        # Select user for update to lock the row and prevent race conditions
        user = await conn.fetchrow(
            "SELECT credits FROM public.users WHERE id = $1 FOR UPDATE", user_id
        )
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        current_credits = user["credits"]
        if current_credits < abs(amount):
            raise HTTPException(
                status_code=403,
                detail="Số dư credit không đủ để thực hiện thao tác này.",
            )

        new_credits = current_credits + amount

        # Update credits
        await conn.execute(
            "UPDATE public.users SET credits = $1, updated_at = now() WHERE id = $2",
            new_credits,
            user_id,
        )

        # Record ledger record
        await conn.execute(
            "INSERT INTO public.credit_transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
            user_id,
            amount,
            tx_type,
            description,
        )

        return new_credits


async def reserve_credits(user_id, amount: int, tx_type: str, description: str) -> int:
    """
    Reserve credits before expensive work starts.

    The reservation is a normal negative ledger entry so concurrent requests
    cannot all pass the same stale balance check.
    """
    if amount <= 0:
        raise ValueError("Reservation amount must be positive.")
    return await deduct_credits(
        user_id=user_id,
        amount=-amount,
        tx_type=tx_type,
        description=description,
    )


async def add_credits(user_id, amount: int, tx_type: str, description: str) -> int:
    """
    Transactionally adds credits to a user profile and logs a transaction ledger record.
    Returns the new credit balance.
    """
    if amount <= 0:
        raise ValueError("Addition amount must be positive.")

    if not Database.pool:
        await Database.connect()

    async with Database.pool.acquire() as conn, conn.transaction():
        user = await conn.fetchrow(
            "SELECT credits FROM public.users WHERE id = $1 FOR UPDATE", user_id
        )
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

        new_credits = user["credits"] + amount

        # Update credits
        await conn.execute(
            "UPDATE public.users SET credits = $1, updated_at = now() WHERE id = $2",
            new_credits,
            user_id,
        )

        # Record ledger record
        await conn.execute(
            "INSERT INTO public.credit_transactions (user_id, amount, type, description) VALUES ($1, $2, $3, $4)",
            user_id,
            amount,
            tx_type,
            description,
        )

        return new_credits


async def refund_credits(user_id, amount: int, tx_type: str, description: str) -> int:
    """
    Return a previously reserved credit after an operation fails.
    """
    if amount <= 0:
        raise ValueError("Refund amount must be positive.")
    return await add_credits(
        user_id=user_id,
        amount=amount,
        tx_type=tx_type,
        description=description,
    )
