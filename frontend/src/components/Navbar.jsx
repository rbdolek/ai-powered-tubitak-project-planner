/* src/components/Navbar.jsx */
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";   // ⬅️ yol düzeltildi
import Avatar from "./Avatar";                  // (isteğe bağlı)
import "../Auth.css";

export default function Navbar() {
    const { user, logoutUser } = useAuth();              // ⬅️ yeni isim

    return (
        <header className="nav">
            <Link className="brand" to="/">TÜBİTAK Chat</Link>
            <div className="nav-gap" />

            {user ? (
                <>
                    {/* Küçük avatar eklemek istersen bu satırın yorumunu aç */}
                    {/* <Avatar src={user.profile.profile_picture} size={24} alt="mini-avatar" /> */}

                    <span className="nav-user">Merhaba, {user.username}</span>

                    <button className="auth-btn-small" onClick={logoutUser}>
                        Çıkış
                    </button>
                </>
            ) : (
                <>
                    <Link className="nav-link" to="/login">Giriş</Link>
                    <Link className="nav-link" to="/register">Kayıt</Link>
                </>
            )}
        </header>
    );
}
