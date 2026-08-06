import { useState } from "react";
import { useAuth } from "../contexts/useAuth";
import { Link, useNavigate } from "react-router-dom";
import "../Auth.css";

export default function Login() {
    const { login } = useAuth();
    const navigate = useNavigate();                  // ← ekle
    const [form, setForm] = useState({ username: "", password: "" });
    const [err, setErr] = useState("");

    const submit = async (e) => {
        e.preventDefault();
        setErr("");                                     // eski hatayı temizle
        try {
            await login(form.username, form.password);    // backend → cookie + user
            navigate("/");                                // ← SPA yönlendirme
        } catch {
            setErr("Kullanıcı adı veya şifre hatalı");
        }
    };

    return (
        <div className="auth-wrapper">
            <form className="auth-card" onSubmit={submit}>
                <h1 className="auth-title">Giriş Yap</h1>

                <input
                    className="auth-input"
                    placeholder="Kullanıcı adı"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                />
                <input
                    className="auth-input"
                    type="password"
                    placeholder="Şifre"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                />

                {err && <div className="auth-error">{err}</div>}

                <button className="auth-btn">Giriş</button>

                <p className="auth-switch">
                    Hesabınız yok mu? <Link to="/register">Kayıt ol</Link>
                </p>
            </form>
        </div>
    );
}
