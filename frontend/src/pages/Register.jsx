import { useState } from "react";
import { register } from "../endpoints/api";
import { Link, useNavigate } from "react-router-dom";
import "../Auth.css";

export default function Register() {
    const nav = useNavigate();
    const [form, setForm] = useState({
        username: "",
        email: "",
        password: "",
    });
    const [err, setErr] = useState("");

    const submit = async (e) => {
        e.preventDefault();
        try {
            await register(form.username, form.email, form.password);
            nav("/login");
        } catch {
            setErr("Kullanıcı adı veya e-posta mevcut.");
        }
    };

    return (
        <div className="auth-wrapper">
            <form className="auth-card" onSubmit={submit}>
                <h1 className="auth-title">Kayıt Ol</h1>

                <input
                    className="auth-input"
                    placeholder="Kullanıcı adı"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                />
                <input
                    className="auth-input"
                    type="email"
                    placeholder="E-posta"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                />
                <input
                    className="auth-input"
                    type="password"
                    placeholder="Şifre"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                />

                {err && <div className="auth-error">{err}</div>}

                <button className="auth-btn">Kayıt</button>

                <p className="auth-switch">
                    Zaten hesabınız var mı? <Link to="/login">Giriş yap</Link>
                </p>
            </form>
        </div>
    );
}
