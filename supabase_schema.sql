-- Tabla de perfiles de usuario
CREATE TABLE profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'starter', 'pro', 'business')),
    evaluations_this_month INTEGER DEFAULT 0,
    evaluations_total INTEGER DEFAULT 0,
    stripe_customer_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tabla de evaluaciones
CREATE TABLE evaluations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES profiles(id),
    input_type TEXT CHECK (input_type IN ('text', 'image')),
    input_product TEXT,
    input_price INTEGER,
    input_description TEXT,
    output_score DECIMAL,
    output_decision TEXT,
    output_full JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger para crear perfil automáticamente
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- RLS Policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE evaluations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

CREATE POLICY "Users can view own evaluations"
    ON evaluations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own evaluations"
    ON evaluations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Función para resetear contador mensual (cron job)
CREATE OR REPLACE FUNCTION reset_monthly_evaluations()
RETURNS void AS $$
BEGIN
    UPDATE profiles SET evaluations_this_month = 0;
END;
$$ LANGUAGE plpgsql;
