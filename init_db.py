import asyncio
from getpass import getpass
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models import Users, BinanceKeys
from auth import pwd_context, encrypt_key

async def crear_usuario(db:AsyncSession , username: str, password: str):
    password_hash = pwd_context.hash(password)
    nuevo_usuario = Users(
        username=username,
        password_hash=password_hash,
        is_active=True,
    )
    db.add(nuevo_usuario)
    await db.flush()
    await db.refresh(nuevo_usuario)
    print(f"Usuario '{username}' creado correctamente.")
    return nuevo_usuario

async def subir_api_key(db:AsyncSession, user: Users):
    alias = input("Alias de las Keys: ").strip()
    public_key = getpass("Public Key: ").strip()
    private_key = getpass("Private Key: ").strip()

    public_key = encrypt_key(public_key)
    private_key = encrypt_key(private_key)
    new_binance_apis = BinanceKeys(
        user_id=user.id,
        api_key=public_key,
        api_secret=private_key,
        alias=alias
    )
    db.add(new_binance_apis)
    await db.flush()
    

async def main():
    async with AsyncSessionLocal() as db:
        print("=== Crear usuario inicial ===")
        username = input("Username: ").strip()
        password = getpass("Password: ").strip()
        confirm = getpass("Confirmar password: ").strip()

        if password != confirm:
            print("Las contraseñas no coinciden. Abortando.")
            return

        nuevo_usuario = await crear_usuario(db, username, password)
        opcion = input("Desea ingresar las API_KEY de Binance?:(Y/N)")
        if opcion.lower() in ["y","yes"]:
            await subir_api_key(db, nuevo_usuario)

        await db.commit()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\n=== PROGRAMA TERMINADO POR EL USUARIO ===")
