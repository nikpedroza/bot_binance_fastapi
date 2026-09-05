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