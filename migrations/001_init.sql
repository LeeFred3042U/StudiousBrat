CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE student_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT,
    grade_level TEXT,
    subjects TEXT[],
    preferred_universe TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
    topic TEXT,
    universe TEXT,
    sub_concepts JSONB,
    has_sequence BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'ended')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX idx_sessions_student_id ON sessions(student_id);

CREATE TABLE session_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('student', 'ai')),
    content TEXT,
    message_type TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_session_messages_session_id ON session_messages(session_id);

CREATE TABLE evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    student_analogy TEXT,
    sub_concepts_covered JSONB,
    sub_concepts_missing JSONB,
    relationship_correct BOOLEAN,
    coverage_pct NUMERIC(5,2),
    band TEXT CHECK (band IN ('Strong', 'Partial', 'Needs work')),
    feedback TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_evaluations_session_id ON evaluations(session_id);

CREATE TABLE generated_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    asset_type TEXT,
    content JSONB,
    url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_generated_assets_session_id ON generated_assets(session_id);

CREATE TABLE learner_state (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES student_profiles(id) ON DELETE CASCADE,
    topic TEXT,
    mastery_estimate FLOAT,
    misconceptions JSONB,
    review_schedule JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_learner_state_student_id ON learner_state(student_id);
