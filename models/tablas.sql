CREATE TABLE public.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    last_login timestamp with time zone
);
 
-- Tabla nueva binance_keys, con user_id como UUID también
CREATE TABLE public.binance_keys (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES users(id),
    api_key text NOT NULL,
    api_secret text NOT NULL,
    alias character varying(50)
);

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE public.trades (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE SET NULL,
    entrada numeric NOT NULL,
    salida numeric NOT NULL,
    tipo character varying(10) NOT NULL,
    razon_salida character varying(50),
    pnl_neto numeric NOT NULL,
    comision numeric,
    funding_total numeric,
    tiempo_entrada timestamp without time zone,
    tiempo_salida timestamp without time zone,
    balance_acumulado numeric,
    strategy character varying(10) NOT NULL,
    order_id_market bigint,
    order_id_sl bigint,
    order_id_tp bigint,
    created_at timestamp without time zone DEFAULT now()
);