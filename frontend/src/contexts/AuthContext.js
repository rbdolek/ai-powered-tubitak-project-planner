import {
    createContext,
    useContext,
    useEffect,
    useState,
    useCallback,
} from "react";
import {
    api,
    token as tokenStore,
    login as apiLogin,
    logout as apiLogout,
    register as apiRegister,
    authenticated_user,
} from "../endpoints/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    /* Ortak profil çekme */
    const fetchProfile = useCallback(async () => {
        setLoading(true);
        try {
            if (!tokenStore.get()) return;
            const userData = await authenticated_user();
            setUser(userData);
        } finally {
            setLoading(false);
        }
    }, []);

    /* İlk yüklenme */
    useEffect(() => { fetchProfile(); }, [fetchProfile]);

    /* Giriş */
    const loginUser = async (username, password) => {
        setError(null);
        await apiLogin(username, password);   // token set edilir
        await fetchProfile();                 // güncel profil
    };

    /* Çıkış */
    const logoutUser = async () => {
        setLoading(true);
        try {
            await apiLogout();
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    /* Kayıt */
    const registerUser = async (fields) => {
        setError(null);
        await apiRegister(fields);
        await fetchProfile();
    };

    /* Profil güncelle */
    const updateProfile = async (data) => {
        setError(null);
        await api.patch("users/profile/", data);
        await fetchProfile();
    };

    /* Profil resmi */
    const uploadProfilePicture = async (file) => {
        const form = new FormData();
        form.append("file", file);
        await api.post("users/upload_profile_picture/", form, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        await fetchProfile();
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                loading,
                error,
                loginUser,
                logoutUser,
                registerUser,
                updateProfile,
                uploadProfilePicture,
                fetchProfile,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within AuthProvider");
    return ctx;
};
