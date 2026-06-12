import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import custom_llm_server as s  # noqa: E402

def _u(t): return [s.UserMessage(role="user", content=t)]
def db():
    p = os.path.join(tempfile.mkdtemp(), "home.db"); return s.get_db(p), p

def test_default_mode_is_living_room():
    conn, _ = db()
    assert s.get_mode(conn) == "living_room"

def test_set_mode_changes_available_tools():
    conn, _ = db()
    s.run_agent_turn(conn, _u("switch to the kitchen"))
    assert s.get_mode(conn) == "kitchen"

def test_device_control_gated_by_mode():
    conn, _ = db()
    on = s.run_agent_turn(conn, _u("turn on the tv"))
    assert "tv" in on.lower() and "on" in on.lower()
    s.run_agent_turn(conn, _u("go to the bedroom"))
    blocked = s.run_agent_turn(conn, _u("turn on the tv"))
    assert "bedroom" in blocked.lower()

def test_scene_keyword_runs_batch_regardless_of_mode():
    conn, _ = db()
    reply = s.run_agent_turn(conn, _u("movie night"))
    assert "movie" in reply.lower()
    assert "tv" in s.run_agent_turn(conn, _u("what's the status")).lower()

def test_status_recall_persists_across_connections():
    conn, path = db()
    s.run_agent_turn(conn, _u("turn on the lamp"))
    again = s.run_agent_turn(s.get_db(path), _u("what is on"))
    assert "lamp" in again.lower()
