-- =============================================
-- Base Trading Agent Dashboard — Supabase Schema
-- =============================================
-- รัน SQL นี้ใน Supabase SQL Editor เพื่อสร้างตารางที่จำเป็น

-- ตาราง agent states — เก็บสถานะของ AI agent แต่ละตัว
CREATE TABLE IF NOT EXISTS agent_states (
  agent_id TEXT PRIMARY KEY,
  agent_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'idle',
  current_task TEXT DEFAULT '',
  bubble_message TEXT DEFAULT '',
  avatar_mood TEXT DEFAULT 'neutral',
  last_action_ts TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb
);

-- ตาราง portfolio state — เก็บสถานะพอร์ต
CREATE TABLE IF NOT EXISTS portfolio_state (
  id TEXT PRIMARY KEY DEFAULT 'main',
  equity NUMERIC DEFAULT 10000,
  cash NUMERIC DEFAULT 10000,
  pnl_pct NUMERIC DEFAULT 0,
  positions INTEGER DEFAULT 0,
  trades_today INTEGER DEFAULT 0,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ตาราง trades — เก็บประวัติเทรด
CREATE TABLE IF NOT EXISTS trades (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  price NUMERIC NOT NULL,
  qty NUMERIC NOT NULL,
  reason TEXT DEFAULT '',
  ts TIMESTAMPTZ DEFAULT NOW()
);

-- สร้าง index สำหรับ query เร็ว
CREATE INDEX IF NOT EXISTS idx_trades_ts ON trades (ts DESC);
CREATE INDEX IF NOT EXISTS idx_agent_states_status ON agent_states (status);

-- เปิด Realtime สำหรับทุกตาราง
ALTER PUBLICATION supabase_realtime ADD TABLE agent_states;
ALTER PUBLICATION supabase_realtime ADD TABLE portfolio_state;
ALTER PUBLICATION supabase_realtime ADD TABLE trades;

-- Insert default agent records
INSERT INTO agent_states (agent_id, agent_name, status, bubble_message, avatar_mood) VALUES
  ('strategist', 'Jing (Strategist)', 'idle', 'Ready to analyze market regime', 'neutral'),
  ('analyst', 'Joe (Analyst)', 'idle', 'Waiting for signals', 'neutral'),
  ('critic', 'James (RiskCritic)', 'idle', 'Arms crossed, ready to judge', 'neutral'),
  ('onchain', 'Jade (OnChain)', 'idle', 'Scanning blockchain...', 'neutral'),
  ('risk', 'Jeed (RiskManager)', 'idle', 'Safety systems online', 'neutral'),
  ('engine', 'Jai (Engine)', 'idle', 'All systems nominal', 'neutral')
ON CONFLICT (agent_id) DO NOTHING;

-- ตาราง agent metrics — เก็บ token usage และ cost สำหรับ analytics
CREATE TABLE IF NOT EXISTS agent_metrics (
  id BIGSERIAL PRIMARY KEY,
  agent_id TEXT NOT NULL,
  tokens_in INTEGER DEFAULT 0,
  tokens_out INTEGER DEFAULT 0,
  cost_usd NUMERIC(10,6) DEFAULT 0,
  model TEXT DEFAULT '',
  ts TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_metrics_ts ON agent_metrics (ts DESC);
CREATE INDEX IF NOT EXISTS idx_agent_metrics_agent ON agent_metrics (agent_id);

ALTER PUBLICATION supabase_realtime ADD TABLE agent_metrics;

-- Insert default portfolio
INSERT INTO portfolio_state (id, equity, cash, pnl_pct, positions, trades_today) VALUES
  ('main', 10000, 10000, 0, 0, 0)
ON CONFLICT (id) DO NOTHING;
