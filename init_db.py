import asyncio
from getpass import getpass

from database import AsyncSessionLocal
from models import Users, BinanceKeys
from auth import pwd_context

async def crear_usuario(db, username: str, password: str):
    password_hash = pwd_context.hash(password)
    nuevo_usuario = Users(
        username=username,
        password_hash=password_hash,
        is_active=True,
    )
    db.add(nuevo_usuario)
    await db.commit()
    print(f"Usuario '{username}' creado correctamente.")


async def main():
    async with AsyncSessionLocal() as db:
        print("=== Crear usuario inicial ===")
        username = input("Username: ").strip()
        password = getpass("Password: ").strip()
        confirm = getpass("Confirmar password: ").strip()

        if password != confirm:
            print("Las contraseñas no coinciden. Abortando.")
            return

        await crear_usuario(db, username, password)

if __name__ == "__main__":
    asyncio.run(main())