import axios from "axios";

/* -------------------------------------------------------------------
   GLOBAL AXIOS INSTANCE
------------------------------------------------------------------- */
const API_URL = "http://localhost:8000/api/";

export const api = axios.create({
    baseURL: API_URL,
    withCredentials: true, // cookie tabanlı auth için
});

/* -------------------------------------------------------------------
   CSRF HELPERS
------------------------------------------------------------------- */
function getCsrfToken() {
    const cookies = document.cookie.split('; ');
    const csrfCookie = cookies.find(cookie => cookie.startsWith('csrftoken='));
    return csrfCookie ? csrfCookie.split('=')[1] : null;
}

export const ensureCsrfToken = async () => {
    try {
        // Django CSRF cookie'sini al
        await api.get("csrf-token/");
    } catch (error) {
        console.error("CSRF token alınamadı:", error);
    }
};

// Her HTTP isteğinde CSRF token header'ı ekle
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';
axios.defaults.withCredentials = true;

/* -------------------------------------------------------------------
   SANITIZE & TITLE HELPERS
------------------------------------------------------------------- */
/**
 * HTML etiketlerini temizler ve karakter sayısını 250 ile sınırlar.
 */
export function sanitizeTitle(rawTitle) {
    const tmp = document.createElement('div');
    tmp.innerHTML = rawTitle;
    let text = tmp.textContent || tmp.innerText || "";
    if (text.length > 250) {
        text = text.substring(0, 250).trim() + "...";
    }
    return text;
}

/* -------------------------------------------------------------------
   TOKEN INTERCEPTOR
------------------------------------------------------------------- */
api.interceptors.request.use(
    (config) => {
        // Token ekleme
        const tok = localStorage.getItem("token");
        const isLogin = config.url?.startsWith("users/login");
        const isRegister = config.method === "post" && config.url === "users/";

        if (tok && !isLogin && !isRegister) {
            config.headers.Authorization = `Token ${tok}`;
        }

        // CSRF token ekleme
        const csrfToken = getCsrfToken();
        if (csrfToken && ["post", "put", "patch", "delete"].includes(config.method)) {
            config.headers["X-CSRFToken"] = csrfToken;
        }

        return config;
    },
    (error) => Promise.reject(error)
);

/* -------------------------------------------------------------------
   TOKEN HELPERS
------------------------------------------------------------------- */
export const token = {
    get: () => localStorage.getItem("token"),
    set: (v) => localStorage.setItem("token", v),
    remove: () => localStorage.removeItem("token"),
};

/* -------------------------------------------------------------------
   AUTH SERVICES
------------------------------------------------------------------- */
export const authenticated_user = async () => {
    try {
        const { data } = await api.get("users/profile/");
        return data;
    } catch {
        token.remove();
        return null;
    }
};

export const login = async (username, password) => {
    // CSRF token'ı önce al
    await ensureCsrfToken();

    const { data } = await api.post("users/login/", { username, password });
    token.set(data.token);
    return data.user;
};

export const logout = async () => {
    await api.post("users/logout/");
    token.remove();
};

export const register = async (userData) => {
    await ensureCsrfToken();
    try {
        const { data } = await api.post("users/", {
            username: userData.username,
            email: userData.email,
            password: userData.password,
            first_name: userData.first_name,
            last_name: userData.last_name,
        });
        token.set(data.token);
        return data.user;
    } catch (error) {
        console.error("Registration error response:", error.response?.data);
        throw error;
    }
};

/* -------------------------------------------------------------------
   CHAT SESSION & MESSAGE ENDPOINTS
------------------------------------------------------------------- */
export const cleanupChatSessions = async () => api.post("chat_sessions/cleanup/");

export const getChatSessions = async () => {
    const res = await api.get("chat_sessions/");
    if (res.data && Array.isArray(res.data)) {
        res.data.sort((a, b) => b.id - a.id);
    }
    return res.data;
};

export const getChatSession = async (sessionId) => {
    const res = await api.get(`chat_sessions/${sessionId}/`);
    return res.data;
};

export const getChatSessionMessages = async (sessionId) => {
    const res = await api.get(`chat_sessions/${sessionId}/messages/`);
    return res.data;
};

export const updateChatSession = async (sessionId, titleOrPayload) => {
    if (!sessionId) throw new Error("sessionId gerekli");

    const raw = typeof titleOrPayload === "string"
        ? { title: titleOrPayload }
        : titleOrPayload;

    const payload = {};
    if (raw.title && typeof raw.title === 'string') {
        const clean = sanitizeTitle(raw.title.trim());
        if (clean) payload.title = clean;
    }

    if (!Object.keys(payload).length) return;

    try {
        const { data } = await api.patch(`chat_sessions/${sessionId}/`, payload);
        console.log("Oturum güncellendi:", data.id, data.title);
        return data;
    } catch (error) {
        console.error("PATCH 400 detay:", error.response?.data);
        throw error;
    }
};

export const deleteChatSession = async (sessionId) => {
    const res = await api.delete(`chat_sessions/${sessionId}/`);
    return res.status === 204;
};

export const createChatSession = async (aiModel = 'openai') => {
    const timestamp = new Date().toLocaleTimeString();
    const { data } = await api.post('chat_sessions/', { title: `Yeni Sohbet (${timestamp})`, ai_model: aiModel });
    return data;
};

export const sendMessage = async (sessionId, message, raw_input) => {
    const payload = raw_input ? { message, raw_input } : { message };
    const { data } = await api.post(`chat_sessions/${sessionId}/send_message/`, payload);
    return data;
};

/* -------------------------------------------------------------------
   PDF GENERATION
------------------------------------------------------------------- */
export const downloadSessionPdf = async (sessionId) => {
    if (!sessionId) {
        throw new Error("PDF indirmek için Session ID gereklidir.");
    }

    const res = await api.get(`chat_sessions/${sessionId}/downloadSessionPdf/`, {
        responseType: "blob",
    });

    if (res.status !== 200) {
        throw new Error(`PDF alınamadı: Sunucu durumu ${res.status}`);
    }

    const blob = new Blob([res.data], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `tubitak_plani_${sessionId}.pdf`; // Dosya adını da session'a göre verelim
    document.body.appendChild(link);
    link.click();

    // Linki temizle
    setTimeout(() => {
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }, 100);

    return blob;
};



/* -------------------------------------------------------------------
   PROJECT ENDPOINTS
------------------------------------------------------------------- */
export const getProjects = async () => {
    const res = await api.get("projects/");
    return res.data;
};

export const getProject = async (projectId) => {
    const res = await api.get(`projects/${projectId}/`);
    return res.data;
};

export const createProject = async (projectData) => {
    const res = await api.post("projects/", projectData);
    return res.data;
};

export const updateProject = async (projectId, updateData) => {
    const { data } = await api.patch(`projects/${projectId}/`, updateData);
    return data;
};

export const deleteProject = async (projectId) => {
    const res = await api.delete(`projects/${projectId}/`);
    return res.status === 204;
};

/* -------------------------------------------------------------------
   OPENAI CHAT COMPLETION SERVICE
------------------------------------------------------------------- */
const OPENAI_URL = "https://api.openai.com/v1/chat/completions";
const OPENAI_KEY = process.env.REACT_APP_OPENAI_API_KEY;

export async function askAI(prompt) {
    if (!OPENAI_KEY) throw new Error("OpenAI API key bulunamadı");
    const payload = { model: "gpt-3.5-turbo", messages: [{ role: "user", content: prompt }], max_tokens: 2000, temperature: 0.7 };
    const { data } = await axios.post(OPENAI_URL, payload, { headers: { "Content-Type": "application/json", Authorization: `Bearer ${OPENAI_KEY}` } });
    if (!data.choices?.length) throw new Error("AI yanıtı alınamadı");
    return data.choices[0].message.content;
}

/* -------------------------------------------------------------------
   FUND DURATION ENDPOINTS
------------------------------------------------------------------- */
export const getFundDurations = async () => {
    try {
        const response = await api.get("fund_durations/");
        if (response.status !== 200) throw new Error(`API ${response.status} hatası: ${response.statusText}`);
        const data = response.data;
        if (!Array.isArray(data)) throw new Error("Geçersiz veri formatı: Dizi bekleniyor");
        return data;
    } catch (error) {
        console.error("Fon süreleri alınamadı:", error);
        if (error.response) console.error("Sunucu yanıtı:", error.response.status, error.response.data);
        throw error;
    }
};
export const downloadSessionDoc = async (sessionId) =>
    api.get(`chat_sessions/${sessionId}/generate_doc/`, {
        responseType: 'blob'           // .docx dönecek
    }).then(res => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `plan_${sessionId}.docx`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    });


/* -------------------------------------------------------------------
   EXPORTS
------------------------------------------------------------------- */
export default {
    api,
    sanitizeTitle,
    getCsrfToken,
    ensureCsrfToken,
    token,
    authenticated_user,
    login,
    logout,
    register,
    cleanupChatSessions,
    getChatSessions,
    getChatSession,
    getChatSessionMessages,
    updateChatSession,
    deleteChatSession,
    createChatSession,
    sendMessage,
    //generatePlanPdf,
    //generateProjectPdf,
    getProjects,
    getProject,
    createProject,
    updateProject,
    deleteProject,
    askAI,
    getFundDurations
};
