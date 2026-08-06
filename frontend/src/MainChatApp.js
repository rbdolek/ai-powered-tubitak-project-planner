import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import chatLogo from './assets/chatgpt.svg';
import addBtn from './assets/add-30.png';
import rocket from './assets/rocket.svg';
import sendBtn from './assets/send.svg';
import imgLogo from './assets/chatgptLogo.svg';
import { useAuth } from './contexts/AuthContext';
import Avatar from "./components/Avatar";
import {
    createChatSession,
    sendMessage,
    getChatSessions,
    getChatSessionMessages,
    getChatSession,
    deleteChatSession,
    updateChatSession,
    cleanupChatSessions,
    getFundDurations,
    ensureCsrfToken,
    downloadSessionDoc
} from './endpoints/api';
import { useNavigate } from 'react-router-dom';
import Calendar from './components/Calendar';

function MainChatApp() {
    const [input, setInput] = useState("");
    const [chats, setChats] = useState([]);
    const [selectedFon, setSelectedFon] = useState("");
    const [fonSelected, setFonSelected] = useState(false);
    const [projectTopicSet, setProjectTopicSet] = useState(false);
    const [planGenerated, setPlanGenerated] = useState(false);
    const [awaitingDownloadConfirm, setAwaitingDownloadConfirm] = useState(false);
    const [hasRun, setHasRun] = useState(false);
    const [isSidebarOpen, setIsSidebarOpen] = useState(true);
    const [currentSession, setCurrentSession] = useState(null);
    const [aiModel, setAiModel] = useState("openai");
    const [isLoading, setIsLoading] = useState(false);
    const [loadingText, setLoadingText] = useState("Yanıt hazırlanıyor");
    const [apiError, setApiError] = useState(null);
    const [serverError, setServerError] = useState(null);
    const [fundDurations, setFundDurations] = useState({});
    const { user, loading, logoutUser } = useAuth();
    const navigate = useNavigate();
    const [pendingSession, setPendingSession] = useState(false);
    const [chatHistory, setChatHistory] = useState([]);
    const [historyLoading, setHistoryLoading] = useState(false);
    const chatEndRef = useRef(null);
    const [modelLoading, setModelLoading] = useState(false);
    const [lastPlanId, setLastPlanId] = useState(null);
    const [projectCalendars, setProjectCalendars] = useState({});
    const [selectedCalendar, setSelectedCalendar] = useState(null);
    const [showFeedback, setShowFeedback] = useState({});
    const [feedbackComment, setFeedbackComment] = useState("");
    const [submittingFeedback, setSubmittingFeedback] = useState(false);

    // iCal dosyası oluşturma fonksiyonu
    const createICalFile = (calendar) => {
        // iCal başlık bilgileri
        let icalContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//TÜBİTAK Proje Takvimi//TR
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:TÜBİTAK ${calendar.fonCode} - ${calendar.projectTitle}
X-WR-TIMEZONE:Europe/Istanbul
BEGIN:VTIMEZONE
TZID:Europe/Istanbul
X-LIC-LOCATION:Europe/Istanbul
END:VTIMEZONE
`;

        // Projenin başlangıç tarihini al
        const startDate = new Date(calendar.startDate);

        // Her ay için etkinlik oluştur
        calendar.months.forEach(month => {
            // Ay başlangıç tarihi hesapla (başlangıç tarihine ay ekle)
            const monthStartDate = new Date(startDate);
            monthStartDate.setMonth(startDate.getMonth() + month.month - 1);

            // Ay bitiş tarihi (bir sonraki ayın başlangıcı)
            const monthEndDate = new Date(monthStartDate);
            monthEndDate.setMonth(monthStartDate.getMonth() + 1);
            monthEndDate.setDate(monthEndDate.getDate() - 1);

            // Ay için ana etkinlik
            icalContent += `BEGIN:VEVENT
UID:month-${month.month}-${Date.now()}@tubitak.gov.tr
DTSTAMP:${formatDateForICal(new Date())}
DTSTART;VALUE=DATE:${formatDateForICal(monthStartDate, true)}
DTEND;VALUE=DATE:${formatDateForICal(monthEndDate, true)}
SUMMARY:Ay ${month.month}: ${month.title}
DESCRIPTION:${month.tasks.join('\\n')}
STATUS:CONFIRMED
TRANSP:TRANSPARENT
END:VEVENT
`;

            // Her görev için ayrı etkinlik
            month.tasks.forEach((task, index) => {
                // Görev tarihini hesapla (ayın belirli günleri)
                const taskDate = new Date(monthStartDate);
                taskDate.setDate(taskDate.getDate() + (index * 2) + 3); // Görevi ayın farklı günlerine dağıt

                // Görev bitiş tarihi
                const taskEndDate = new Date(taskDate);
                taskEndDate.setDate(taskEndDate.getDate() + 7); // Görevlerin 1 hafta süreceğini varsay

                icalContent += `BEGIN:VEVENT
UID:task-${month.month}-${index}-${Date.now()}@tubitak.gov.tr
DTSTAMP:${formatDateForICal(new Date())}
DTSTART;VALUE=DATE:${formatDateForICal(taskDate, true)}
DTEND;VALUE=DATE:${formatDateForICal(taskEndDate, true)}
SUMMARY:${task}
DESCRIPTION:Ay ${month.month}: ${month.title}\\n${task}
STATUS:CONFIRMED
TRANSP:TRANSPARENT
END:VEVENT
`;
            });
        });

        // Takvimi kapat
        icalContent += "END:VCALENDAR";

        return icalContent;
    };

    // Tarihi iCal formatına dönüştüren yardımcı fonksiyon
    const formatDateForICal = (date, dateOnly = false) => {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');

        if (dateOnly) {
            return `${year}${month}${day}`;
        }

        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const seconds = date.getSeconds().toString().padStart(2, '0');

        return `${year}${month}${day}T${hours}${minutes}${seconds}Z`;
    };

    // Plan mesajı kontrolü için yardımcı fonksiyon
    const isPlanMessage = (text) => {
        console.log("Plan kontrolü yapılıyor:", text.substring(0, 50));

        // Regex ile "Ay X:" formatını ara
        const ayPattern = /Ay \d+:/g;
        const matches = text.match(ayPattern);

        // Sonucu logla
        console.log("Bulunan ay sayısı:", matches ? matches.length : 0);

        if (matches && matches.length > 1) {
            return true;
        }

        // Alternatif yöntem: "ay" ve ayların numaralarını içeriyor mu?
        if (text.includes("Ay 1:") &&
            text.includes("Ay 2:") &&
            text.includes("Ay 3:")) {
            console.log("Alternatif yöntemle plan tespit edildi");
            return true;
        }

        return false;
    };

    // Takvim oluşturma fonksiyonu
    const createCalendarFromPlan = (planText, chatId, fonCode, projectTitle) => {
        console.log("Takvim oluşturuluyor...");

        // Plan metninden ayları ve görevleri ayıkla
        const monthRegex = /Ay (\d+): ([^\n]+)([\s\S]*?)(?=Ay \d+:|$)/g;
        const taskRegex = /-\s*([^\n]+)/g;

        const months = [];
        let match;

        while ((match = monthRegex.exec(planText)) !== null) {
            const monthNumber = parseInt(match[1]);
            const monthTitle = match[2].trim();
            const monthContent = match[3].trim();

            const tasks = [];
            let taskMatch;

            while ((taskMatch = taskRegex.exec(monthContent)) !== null) {
                tasks.push(taskMatch[1].trim());
            }

            months.push({
                month: monthNumber,
                title: monthTitle,
                tasks: tasks
            });
        }

        console.log("Ayıklanan aylar:", months);

        if (months.length === 0) {
            console.error("Plan metni ayrıştırılamadı!");
            alert("Plan metni ayrıştırılamadı. Lütfen geçerli bir plan metni olduğundan emin olun.");
            return null;
        }

        // Proje zaman çizelgesi hesapla
        const startDate = new Date();
        const endDate = new Date();
        const duration = months.length;
        endDate.setMonth(endDate.getMonth() + duration);

        // Takvim veri yapısı oluştur
        const calendarId = Date.now().toString();
        const calendar = {
            id: calendarId,
            fonCode: fonCode,
            projectTitle: projectTitle,
            months: months,
            startDate: startDate,
            endDate: endDate,
            duration: duration,
            sourceChatId: chatId
        };

        console.log("Oluşturulan takvim:", calendar);

        // Takvimi state'e ekle
        setProjectCalendars(prev => {
            const newCalendars = { ...prev, [calendarId]: calendar };

            // localStorage'a kaydet
            try {
                localStorage.setItem('projectCalendars', JSON.stringify(newCalendars));
            } catch (e) {
                console.error('Takvim kaydedilemedi:', e);
            }

            return newCalendars;
        });

        return calendarId;
    };

    // Planı takvime dönüştürme işleyicisi
    const handleCreateCalendar = (planText, chatId) => {
        // Fon ve proje bilgilerini al
        const title = currentSession?.title || '';

        // Fon kodunu ve proje başlığını ayıkla
        const fonMatch = title.match(/^([\w-]+)\s*-\s*(.+)$/);
        const fonCode = fonMatch ? fonMatch[1] : selectedFon || "TÜBİTAK";
        const projectTitle = fonMatch ? fonMatch[2] : title || "Proje";

        // Takvim oluştur
        const calendarId = createCalendarFromPlan(planText, chatId, fonCode, projectTitle);

        if (calendarId) {
            // Takvimi seç
            setSelectedCalendar(calendarId);

            // Takvim oluşturuldu işaretini ekle
            setChats(prevChats =>
                prevChats.map(chat =>
                    chat.id === chatId ? { ...chat, calendarCreated: true } : chat
                )
            );

            // Başarı mesajı göster
            alert('Takvim başarıyla oluşturuldu! Yan menüden görüntüleyebilirsiniz.');

            // Takvimi indirmek ister misiniz diye sor (window.confirm kullanarak ESLint hatasını önle)
            const wantToDownload = window.confirm('Takvimi bilgisayarınıza indirmek ister misiniz?');
            if (wantToDownload) {
                handleDownloadCalendar(calendarId);
            }
        }
    };

    // Takvimi indirme işleyicisi
    const handleDownloadCalendar = (calendarId) => {
        const calendar = projectCalendars[calendarId];
        if (!calendar) {
            alert("Takvim bulunamadı!");
            return;
        }

        // iCal dosyası oluştur
        const icalContent = createICalFile(calendar);

        // Dosyayı indirme
        const blob = new Blob([icalContent], { type: 'text/calendar;charset=utf-8' });
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = `TÜBİTAK_${calendar.fonCode}_Proje_Takvimi.ics`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        // Kullanıcıya takvim kullanımı hakkında bilgi ver
        showCalendarInstructions();
    };

    // Takvim kullanımı hakkında bilgi gösteren fonksiyon
    const showCalendarInstructions = () => {
        alert(`Takvimi içe aktarmak için:
    
1. İndirdiğiniz .ics dosyasını çift tıklayın veya takvim uygulamanızı açın.

2. Google Takvim:
   - Sağ üst köşedeki "+" ikonuna tıklayın
   - "İçe aktar" seçeneğini seçin
   - İndirdiğiniz .ics dosyasını seçin

3. Outlook:
   - "Dosya" > "Aç ve Dışa Aktar" > "İçe Aktar/Dışa Aktar"
   - "iCalendar (.ics) dosyasını içe aktar" seçeneğini seçin
   - İndirdiğiniz .ics dosyasını seçin

4. Apple Takvim:
   - "Dosya" > "İçe Aktar" seçeneğini seçin
   - İndirdiğiniz .ics dosyasını seçin`);
    };

    // Takvim verilerini localStorage'dan yükle
    const loadCalendarsFromStorage = () => {
        try {
            const savedCalendarsJson = localStorage.getItem('projectCalendars');
            if (savedCalendarsJson) {
                const savedCalendars = JSON.parse(savedCalendarsJson);

                // Tarihleri String'den Date'e dönüştür
                Object.values(savedCalendars).forEach(calendar => {
                    calendar.startDate = new Date(calendar.startDate);
                    calendar.endDate = new Date(calendar.endDate);
                });

                console.log("Kaydedilmiş takvimler yüklendi:", savedCalendars);
                setProjectCalendars(savedCalendars);
            }
        } catch (e) {
            console.error('Takvimler yüklenemedi:', e);
        }
    };

    // Fon sürelerini yükleme fonksiyonu
    const loadFundDurations = async () => {
        try {
            setApiError(null);
            console.log("Fon süreleri yükleniyor...");

            const data = await getFundDurations();
            console.log("Fon süreleri API'den alındı:", data);

            // Boş veri kontrolü
            if (!data || data.length === 0) {
                throw new Error("Fon süreleri veritabanından boş geldi");
            }

            // Veri formatını map'e dönüştür
            const map = {};
            data.forEach(item => {
                if (item && item.code && item.duration_months) {
                    map[item.code] = item.duration_months;
                } else {
                    console.warn("Geçersiz fon süresi öğesi:", item);
                }
            });

            // En az bir öğe var mı kontrol et
            if (Object.keys(map).length === 0) {
                throw new Error("Hiçbir geçerli fon süresi bulunamadı");
            }

            setFundDurations(map);
            console.log("Fon süreleri başarıyla yüklendi:", map);
        } catch (error) {
            console.error("Fon süreleri yüklenirken hata:", error);
            setApiError(`Fon süreleri yüklenemedi: ${error.message}`);

            // Varsayılan değerler kullan
            const defaultDurations = {
                "2209-A": 12,
                "2209-B": 12,
                "2247-C": 6,
                "2205": 12
                // Diğer fonlar için varsayılan değerler...
            };

            setFundDurations(defaultDurations);
            console.log("Varsayılan fon süreleri kullanılıyor:", defaultDurations);
        }
    };

    // Sohbet geçmişini yükleme
    const loadChatHistory = async () => {
        setHistoryLoading(true);
        try {
            const sessions = await getChatSessions();

            // Başlık olarak ilk mesajı kullanalım
            const filtered = sessions.filter(s => s.message_count > 0).map(session => {
                // Başlık ayarı: Eğer başlık bir fon kodu içeriyorsa (örn: 2209-A) başlığı koru
                // Aksi halde ilk kullanıcı mesajını başlık olarak kullan
                const hasFonCode = session.title && /\d{4}-[A-Z]/.test(session.title);

                // Başlığı düzenle
                if (!hasFonCode && session.first_message) {
                    session.title = session.first_message.length > 30
                        ? session.first_message.substring(0, 30) + "..."
                        : session.first_message;
                }

                return session;
            });

            setChatHistory(filtered);
        } catch (err) {
            console.error("Geçmiş yüklenirken hata:", err);
            setApiError("Sohbet geçmişi yüklenemedi.");
        } finally {
            setHistoryLoading(false);
        }
    };

    const loadChatSession = async (sessionId) => {
        try {
            setIsLoading(true);
            setLoadingText("Sohbet yükleniyor...");

            // 1) Oturumu çek ve state'e ata
            const sessionObj = await getChatSession(sessionId);
            setCurrentSession(sessionObj);

            // 2) Mesajları yükle
            const messages = await getChatSessionMessages(sessionId);
            setChats(messages.map(msg => ({
                id: msg.id || Date.now().toString(),
                sender: msg.is_user ? "user" : "bot",
                text: msg.content
            })));

            // 3) Eğer plan oluşturulduysa PDF otomatik indirme isteği
            if (lastPlanId) {
                await downloadSessionDoc(lastPlanId);
            }

            // Durumları resetle
            setPlanGenerated(false);
            setAwaitingDownloadConfirm(false);
            setFonSelected(false);
            setProjectTopicSet(false);

        } catch (error) {
            console.error("Sohbet yüklenirken hata:", error);
            setApiError("Sohbet yüklenemedi.");
        } finally {
            setIsLoading(false);
            setLoadingText("Yanıt hazırlanıyor");
        }
    };

    // Sohbet oturumunu silme
    const handleDeleteSession = async (sessionId, event) => {
        // Tıklama olayının yayılmasını engelle
        event.stopPropagation();

        try {
            await deleteChatSession(sessionId);
            setChatHistory(prev => prev.filter(session => session.id !== sessionId));

            // Eğer silinen oturum şu an açık olan oturumsa, yeni bir oturum başlat
            if (currentSession && currentSession.id === sessionId) {
                startNewChatSession();
            }
        } catch (error) {
            console.error("Sohbet silinirken hata:", error);
            setApiError("Sohbet silinemedi. Lütfen tekrar deneyin.");
        }
    };

    const startNewChatSession = useCallback(() => {
        // 1) Herhangi bir hata veya loading durumunu sıfırla
        setApiError(null);
        setServerError(null);

        // 2) "Beklemede session" flag'ini aktif et
        //    (Henüz backend'e session kaydı atılmadı demek)
        setPendingSession(true);
        setCurrentSession(null);

        // 3) Chat penceresini yalnızca "karşılama" mesajıyla doldur
        setChats([
            {
                id: Date.now().toString(),
                sender: "bot",
                text: "Merhaba! TÜBİTAK fonları hakkında yardımcı olabilirim. Lütfen bir fon seçiniz.",
                type: "fonSecimi",  // Eğer bu type'ı kullanıyorsanız, yoksa silebilirsiniz
            }
        ]);

        // 4) Sohbet geçmişini (DB'de gerçek mesaj atan seansları) yeniden yükle
        //    (Yalnızca message_count > 0 olanlar listelenecek)
        loadChatHistory();
    }, []);

    // Geri bildirim toggleFunc
    const toggleFeedback = (chatId) => {
        const newShowFeedback = { ...showFeedback };
        newShowFeedback[chatId] = !newShowFeedback[chatId];
        setShowFeedback(newShowFeedback);
    };

    // Geri bildirim gönderme fonksiyonu
    const submitFeedback = async (chatId, rating) => {
        try {
            setSubmittingFeedback(true);

            // Belirli ID'ye sahip mesajı bul
            const botChat = chats.find(chat => chat.id === chatId);

            if (!botChat) {
                console.error("Geri bildirim için mesaj bulunamadı");
                return;
            }

            // En son kullanıcı mesajını bul (veya ilgili soruyu)
            // Not: Bu daha karmaşık bir mantık gerektirebilir
            const userChats = chats.filter(chat => chat.sender === "user");
            const lastUserChat = userChats[userChats.length - 1];

            if (!lastUserChat) {
                console.error("Kullanıcı mesajı bulunamadı");
                return;
            }

            // API'ye gönderilecek veri
            const feedbackData = {
                query: lastUserChat.text,
                response: botChat.text,
                score: rating,
                comment: feedbackComment,
                features: {
                    // Özellikler ekleyebilirsiniz, örneğin:
                    ai_model: aiModel,
                    // Eğer fon seçildiyse:
                    selected_fund: selectedFon || null,
                    // Diğer özellikler...
                }
            };

            // API çağrısı
            const response = await fetch('/api/feedback/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.cookie.split('; ')
                        .find(row => row.startsWith('csrftoken'))
                        ?.split('=')[1] || '',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(feedbackData)
            });

            if (!response.ok) {
                throw new Error('Geri bildirim gönderilemedi');
            }

            // Geri bildirim durumunu sıfırla
            const newShowFeedback = { ...showFeedback };
            newShowFeedback[chatId] = false;
            setShowFeedback(newShowFeedback);
            setFeedbackComment("");

            // Kullanıcıyı bilgilendir
            alert("Geri bildiriminiz için teşekkürler!");

        } catch (error) {
            console.error("Geri bildirim hatası:", error);
            alert("Geri bildirim gönderilirken bir hata oluştu.");
        } finally {
            setSubmittingFeedback(false);
        }
    };

    useEffect(() => {
        // Uygulama başlatılırken CSRF token'ı al
        if (user && !loading) {
            ensureCsrfToken().then(() => {
                // Fon sürelerini yükle
                loadFundDurations();

                // Sohbet geçmişini yükle
                loadChatHistory();

                // Takvimleri yükle
                loadCalendarsFromStorage();
            });
        }
    }, [user, loading]);

    // Sayfa yüklendiğinde sohbet geçmişini kontrol et
    useEffect(() => {
        if (!hasRun && user && !loading) {
            console.log("Sayfa yüklendi, sohbet geçmişi kontrol ediliyor...");

            // Tüm işlemleri bir async fonksiyonda topla
            const initializeChat = async () => {
                try {
                    const sessions = await getChatSessions();
                    console.log(`${sessions.length} adet sohbet bulundu`);

                    if (sessions && sessions.length > 0) {
                        // En son sohbeti yükle
                        console.log(`En son sohbet (ID: ${sessions[0].id}) yükleniyor...`);
                        await loadChatSession(sessions[0].id);
                    } else {
                        // Sohbet yok, yeni başlat
                        console.log("Sohbet geçmişi bulunamadı, yeni başlatılıyor...");
                        await startNewChatSession();
                    }
                } catch (error) {
                    console.error("Başlangıç hatası:", error);
                    console.log("Hata nedeniyle yeni sohbet başlatılıyor...");
                    await startNewChatSession();
                } finally {
                    setHasRun(true);
                }
            };

            // Başlatma fonksiyonunu çağır
            initializeChat();
        }
    }, [hasRun, user, loading, startNewChatSession]);

    // Mesajlara her eklemede en alta scroll
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chats]);

    useEffect(() => {
        if (!loading && !user) {
            navigate('/login');
        }
    }, [user, loading, navigate]);

    const toggleSidebar = () => setIsSidebarOpen(prev => !prev);

    const handleFonSelect = (fonCode) => {
        // Fon seçimini kaydet
        setSelectedFon(fonCode);
        setFonSelected(true);

        // Fon süresini al
        const duration = fundDurations[fonCode] || 12; // default 12 ay

        // Mevcut mesajlara ekle
        setChats(prev => [
            ...prev,
            {
                id: Date.now().toString(),
                sender: "bot",
                text: `📋 Seçtiğiniz ${fonCode} programı **${duration} ay** süreli. Lütfen proje konunuzu yazın, size otomatik olarak ${duration} aylık plan oluşturacağım.`
            }
        ]);

        // Sohbet başlığını güncelle - fonun adıyla
        if (currentSession && currentSession.id) {
            const title = `${fonCode} Programı`;
            updateChatSession(currentSession.id, title)
                .then(() => {
                    setCurrentSession(prev => ({ ...prev, title }));
                    console.log(`Sohbet başlığı fon seçimiyle güncellendi: ${title}`);
                })
                .catch(err => console.error("Fon seçiminde başlık güncelleme hatası:", err));
        }
    };

    // MainChatApp.js içindeki handleSend fonksiyonu
    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userInput = input.trim();
        setInput("");
        setIsLoading(true);
        setApiError(null);
        setServerError(null);

        let sessionIdToUse = null;

        try {
            // 1) Eğer hâlâ Yeni Sohbet'e bastı ama backend'de session kaydı yapılmadıysa:
            if (pendingSession) {
                let newSession;
                try {
                    // aiModel değişkeninizi backend'e de yollayın:
                    newSession = await createChatSession(aiModel);
                } catch (err) {
                    console.error("createChatSession hatası:", err);
                    setApiError("Yeni sohbet başlatılamadı. Sunucuya bağlanamıyor.");
                    setIsLoading(false);
                    return;
                }

                // Backend'den geçerli bir session objesi gelmiş mi kontrol et:
                if (!newSession || typeof newSession.id === "undefined") {
                    console.error("Beklenmedik session objesi geldi:", newSession);
                    setApiError("Oturum oluşturulamadı. Lütfen tekrar deneyin.");
                    setIsLoading(false);
                    return;
                }

                // Geçerli bir session geldi, state'i güncelle
                setCurrentSession(newSession);
                setPendingSession(false);
                sessionIdToUse = newSession.id;

                // Artık DB'deki geçmişi yenileyelim (eger varsa eski mesajlar):
                await loadChatHistory();
            }
            // 2) Eğer pendingSession false ve currentSession zaten varsa:
            else if (currentSession && currentSession.id) {
                sessionIdToUse = currentSession.id;
            }
            // 3) Ne pendingSession ne currentSession varsa (ilk kez mesaj atılıyor)
            else {
                let newSession2;
                try {
                    newSession2 = await createChatSession(aiModel);
                } catch (err) {
                    console.error("Yeni oturum yaratma hatası:", err);
                    setApiError("Yeni sohbet başlatılamadı. Tekrar deneyin.");
                    setIsLoading(false);
                    return;
                }
                if (!newSession2 || typeof newSession2.id === "undefined") {
                    console.error("Invalid session döndü:", newSession2);
                    setApiError("Oturum oluşturulamadı. Tekrar deneyin.");
                    setIsLoading(false);
                    return;
                }

                setCurrentSession(newSession2);
                setPendingSession(false);
                sessionIdToUse = newSession2.id;

                await loadChatHistory();
            }

            // Şimdi kesinlikle sessionIdToUse var.
            // 4) Önce UI'a "kullanıcı mesajı"nı ekleyelim:
            setChats(prev => [
                ...prev,
                { id: Date.now().toString(), sender: "user", text: userInput }
            ]);

            // 5) Backend'e gönderilecek "full prompt" ve "raw input" ikilisini hazırlayalım:
            //
            //    Normal bir sohbet mesajıysa:
            //    - fullPrompt = userInput
            //    - rawInput  = userInput
            //
            //    (Eğer projenin planını oluşturma adımındaysak, 
            //     fullPrompt ayrı, rawInput ayrı olacak; 
            //     Aşağıdaki örnekte sadece tek parametre kullandık. 
            const fullPrompt = userInput;
            const rawInput = userInput;

            // 6) Gönderimi yap:
            let response, botText;

            // Proje planı oluşturma adımındaysak farklı bir istek gönder
            if (fonSelected && !projectTopicSet && !planGenerated) {
                setProjectTopicSet(true);
                const duration = fundDurations[selectedFon] || 12;
                const fullPlanPrompt = `
TÜBİTAK ${selectedFon} fonu için "${userInput}" konusunda ${duration} aylık bir proje planı oluştur.
Yanıtını şu formatta ver:

Ay 1: [Bu ay için kısa başlık]
- [Birinci görev]
- [İkinci görev]
- [Üçüncü görev]

Ay 2: [Bu ay için kısa başlık]
- [Birinci görev]
- [İkinci görev]
- [Üçüncü görev]

... diğer aylar ...

Ay ${duration}: [Bu ay için kısa başlık]
- [Birinci görev]
- [İkinci görev]
- [Üçüncü görev]

NOT: Her satırı ayrı bir satır olarak yaz ve her görev maddesi için yeni bir satır kullan. Açıklama yapmadan doğrudan"Ay 1:" ile başla.
`;
                // Plan oluşturma isteği gönder
                const planResponse = await sendMessage(sessionIdToUse, fullPlanPrompt, userInput);
                botText = planResponse.ai_response;

                if (planResponse.plan_id) {
                    setLastPlanId(planResponse.plan_id);
                }

                // Plan düzeltme gerekiyorsa
                if (botText.toLowerCase().includes("konusunda") && botText.toLowerCase().includes("plan")) {
                    const fixPrompt = `
Lütfen istendiği gibi ${duration} aylık bir proje planını doğrudan oluştur. 
Her ay için bir başlık ve 3 görev maddesi olsun.
Açıklama yapmadan veya soruyu tekrarlamadan, doğrudan "Ay 1:" ile başla.
`;
                    const fixResponse = await sendMessage(sessionIdToUse, fixPrompt, userInput);
                    botText = fixResponse.ai_response;
                }

                // Sohbet başlığını güncelle
                const newTitle = `${selectedFon} - ${userInput}`;
                await updateChatSession(sessionIdToUse, newTitle);
                setCurrentSession(prev => ({ ...prev, title: newTitle }));

                // ANAHTAR DEĞİŞİKLİK: 
                // Bu kısımda DOC sorusunun AYRI BİR MESAJ olarak gönderilmesini sağlıyoruz

                // 1. Önce sadece plan metnini ekleyin
                setChats(prev => [
                    ...prev,
                    { id: Date.now().toString(), sender: "bot", text: botText }
                ]);

                // 2. Sonra hemen DOC sorusunu EKLEYİN, ama BEKLETMEDEN
                setChats(prev => [
                    ...prev,
                    {
                        id: Date.now().toString() + "-doc-question",
                        sender: "bot",
                        text: "Plan hazırlandı. DOC olarak indirmek ister misiniz? (evet/hayır)"
                    }
                ]);

                // 3. Durumları güncelleyin
                setPlanGenerated(true);
                setAwaitingDownloadConfirm(true);

                // 4. Geçmişi yükleyin ve işlemi bitirin
                await loadChatHistory();
                setIsLoading(false);
                return; // Diğer işlemlerin çalışmasını engellemek için
            }
            // DOC indirme yanıtı bekliyorsak
            else if (planGenerated && awaitingDownloadConfirm) {
                if (/^(evet|e)$/i.test(userInput)) {
                    setChats(prev => [
                        ...prev,
                        { id: Date.now().toString(), sender: "bot", text: "DOC hazırlanıyor, lütfen bekleyin..." }
                    ]);
                    try {
                        const sessionId = currentSession?.id;
                        if (!sessionId) throw new Error("Oturum bilgisi bulunamadı");
                        await downloadSessionDoc(sessionId);

                        // DOC indirme bilgisini localStorage'a kaydet
                        const docInfo = {
                            id: Date.now().toString(),
                            projectId: sessionId,
                            title: currentSession.title || "İsimsiz Proje",
                            downloadDate: new Date().toISOString(),
                            ai_model_used: aiModel,
                            duration_months: fundDurations[selectedFon] || 12
                        };

                        // Mevcut indirilen DOC'ları al
                        const userDocsKey = `downloadedDocs_${user.id}`;
                        let userDocs = [];
                        const savedDocs = localStorage.getItem(userDocsKey);

                        if (savedDocs) {
                            try {
                                userDocs = JSON.parse(savedDocs);
                            } catch (e) {
                                console.error("DOC bilgileri ayrıştırılamadı:", e);
                                userDocs = [];
                            }
                        }

                        // Yeni DOC'u ekle
                        userDocs.push(docInfo);

                        // localStorage'a kaydet
                        localStorage.setItem(userDocsKey, JSON.stringify(userDocs));
                        console.log("İndirilen DOC bilgisi kaydedildi:", docInfo);

                        setChats(prev => [
                            ...prev,
                            { id: Date.now().toString(), sender: "bot", text: "DOC başarıyla indirildi!" }
                        ]);
                    } catch (err) {
                        console.error("DOC oluşturma hatası:", err);
                        if (err.response && err.response.status === 500) {
                            setServerError("Sunucu hatası: DOC oluşturulamadı.");
                            setChats(prev => [
                                ...prev,
                                {
                                    id: Date.now().toString(),
                                    sender: "bot",
                                    text: "DOC oluşturulurken sorun oluştu. Lütfen sayfayı yenileyip tekrar deneyin."
                                }
                            ]);
                        } else {
                            setChats(prev => [
                                ...prev,
                                {
                                    id: Date.now().toString(),
                                    sender: "bot",
                                    text: "DOC indirilemedi veya proje oluşturulurken hata oluştu."
                                }
                            ]);
                        }
                        setApiError("DOC oluşturma hatası.");
                    }
                } else {
                    setChats(prev => [
                        ...prev,
                        {
                            id: Date.now().toString(),
                            sender: "bot",
                            text: "Tamam, DOC indirmiyoruz."
                        }
                    ]);
                }
                setAwaitingDownloadConfirm(false);
                setIsLoading(false);
                return; // Erken çıkış yaparak normal yanıt işlenmesini engelle
            }
            // Normal sohbet modundaysak
            else {
                response = await sendMessage(sessionIdToUse, fullPrompt, rawInput);
                botText = response.ai_response;

                // Başlık güncelleme - sadece ilk mesajda
                if (!currentSession.title || currentSession.title.includes("Yeni Sohbet")) {
                    const title = userInput.length > 50 ? userInput.substring(0, 50) + "..." : userInput;
                    await updateChatSession(sessionIdToUse, title);
                    setCurrentSession(prev => ({ ...prev, title }));
                }
            }

            // 7) "Bot cevabı" UI'a ekle:
            setChats(prev => [
                ...prev,
                { id: Date.now().toString(), sender: "bot", text: botText }
            ]);

            // Plan oluşturulduysa PDF sorusu ekle
            if (fonSelected && projectTopicSet && !planGenerated) {
                setChats(prev => [
                    ...prev,
                    {
                        id: Date.now().toString() + "-doc-question",
                        sender: "bot",
                        text: "Plan hazırlandı. DOC olarak indirmek ister misiniz? (evet/hayır)"
                    }
                ]);

                setPlanGenerated(true);
                setAwaitingDownloadConfirm(true);
            }

            // Sohbet geçmişini yenile
            await loadChatHistory();

            // "PDF İsteği" kısmı
            if (planGenerated && awaitingDownloadConfirm) {
                if (/^(evet|e)$/i.test(userInput)) {
                    setChats(prev => [
                        ...prev,
                        { id: Date.now().toString(), sender: "bot", text: "DOC hazırlanıyor, lütfen bekleyin..." }
                    ]);
                    try {
                        const sessionId = currentSession?.id;
                        if (!sessionId) throw new Error("Oturum bilgisi bulunamadı");
                        await downloadSessionDoc(sessionId);
                        setChats(prev => [
                            ...prev,
                            { id: Date.now().toString(), sender: "bot", text: "DOC başarıyla indirildi!" }
                        ]);
                    } catch (err) {
                        console.error("DOC oluşturma hatası:", err);
                        if (err.response && err.response.status === 500) {
                            setServerError("Sunucu hatası: DOC oluşturulamadı.");
                            setChats(prev => [
                                ...prev,
                                {
                                    id: Date.now().toString(),
                                    sender: "bot",
                                    text: "DOC oluşturulurken sorun oluştu. Lütfen sayfayı yenileyip tekrar deneyin."
                                }
                            ]);
                        } else {
                            setChats(prev => [
                                ...prev,
                                {
                                    id: Date.now().toString(),
                                    sender: "bot",
                                    text: "DOC indirilemedi veya proje oluşturulurken hata oluştu."
                                }
                            ]);
                        }
                        setApiError("DOC oluşturma hatası.");
                    }
                } else {
                    setChats(prev => [
                        ...prev,
                        {
                            id: Date.now().toString(),
                            sender: "bot",
                            text: "Tamam, DOC indirmiyoruz."
                        }
                    ]);
                }
                setAwaitingDownloadConfirm(false);
                setIsLoading(false);
                return;
            }


            // 10) "Normal sohbet" akışı (daha önce de eklemiştik)
            //    Zaten 6,7 ve 8. adımları yaptıktan sonra:
            if (!fonSelected || planGenerated) {
                // Eğer başlık hâlâ "Yeni Sohbet" ise, ilk kullanıcı mesajıyla güncelle
                if (!currentSession.title || currentSession.title.includes("Yeni Sohbet")) {
                    const title =
                        userInput.length > 50 ? userInput.substring(0, 50) + "..." : userInput;
                    await updateChatSession(sessionIdToUse, title);
                    setCurrentSession(prev => ({ ...prev, title }));
                }
            }

            await loadChatHistory();
        } catch (error) {
            console.error("Yanıt alınamadı:", error);
            setChats(prev => [
                ...prev,
                { id: Date.now().toString(), sender: "bot", text: "Bir hata oluştu. Lütfen tekrar deneyin." }
            ]);
            setApiError("API yanıt vermedi. Lütfen tekrar deneyin.");
        } finally {
            setIsLoading(false);
        }
    };


    const changeAiModel = async (model) => {
        setModelLoading(true);
        setApiError(null);

        try {
            await ensureCsrfToken();

            // 1. currentSession null kontrolü ekleyin
            if (currentSession && currentSession.id) {
                // Sadece mevcut bir oturum varsa güncelle
                const updatedSession = await updateChatSession(
                    currentSession.id,
                    { ai_model: model }
                );
                setCurrentSession(updatedSession);
            } else {
                // Oturum yoksa sadece yerel state'i güncelle
                console.log("Aktif oturum yok, sadece yerel AI modeli değiştiriliyor");
            }

            // AI modelini her durumda güncelle
            setAiModel(model);

            // Sohbet akışını "fon seçimi" adımına sıfırla
            setFonSelected(false);
            setProjectTopicSet(false);
            setPlanGenerated(false);
            setAwaitingDownloadConfirm(false);

            // Chat'leri doğrudan "fonSecimi" bot mesajı ile başlat
            setChats([{
                id: Date.now().toString(),
                sender: "bot",
                text: "Merhaba! TÜBİTAK fonları hakkında yardımcı olabilirim. Lütfen bir fon seçiniz.",
                type: "fonSecimi"
            }]);

            // Eğer fundDurations halen boşsa, yeniden yükle
            if (!fundDurations || Object.keys(fundDurations).length === 0) {
                await loadFundDurations();
            }

            // Oturum yoksa yeni bir oturum başlat
            if (!currentSession) {
                await startNewChatSession();
            }

        } catch (err) {
            console.error("Model değişikliği kaydedilemedi:", err);
            setApiError("Model değişikliği sırasında hata oluştu");
        } finally {
            setModelLoading(false);
        }
    };

    const handleResetApp = () => {
        // Temizleme işlemini yap ve sayfayı yenile
        cleanupChatSessions().then(() => {
            window.location.reload();
        });
    };

    // "X dakika önce", "X saat önce" şeklinde süre farkını hesaplayan fonksiyon
    const getTimeAgo = (dateString) => {
        const now = new Date();
        const past = new Date(dateString);
        const diffMs = now - past;

        // Zaman farkını saniye olarak hesapla
        const diffSec = Math.floor(diffMs / 1000);

        // Saniyeyi dakika, saat, gün vs. çevir
        if (diffSec < 60) {
            return 'şimdi';
        } else if (diffSec < 3600) {
            const minutes = Math.floor(diffSec / 60);
            return `${minutes} dakika önce`;
        } else if (diffSec < 86400) {
            const hours = Math.floor(diffSec / 3600);
            return `${hours} saat önce`;
        } else if (diffSec < 604800) {
            const days = Math.floor(diffSec / 86400);
            return `${days} gün önce`;
        } else if (diffSec < 2592000) {
            const weeks = Math.floor(diffSec / 604800);
            return `${weeks} hafta önce`;
        } else {
            const months = Math.floor(diffSec / 2592000);
            return `${months} ay önce`;
        }
    };

    const fonlar = [
        {
            category: "Lisans/Önlisans Düzeyi",
            items: [
                { code: "2205", name: "Lisans Burs Programı" },
                { code: "2247-C", name: "Stajyer Araştırmacı Burs Programı (STAR)" },
                { code: "BİÇABA", name: "Birlikte Çalışıp Birlikte Başaracağız Burs Programı" },
                { code: "2209-A", name: "Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı" },
                { code: "2209-B", name: "Üniversite Öğrencileri Sanayiye Yönelik Araştırma Projeleri Destekleme Programı" },
                { code: "2248", name: "Mentorluk Desteği Programı" }
            ]
        },
        {
            category: "Lisansüstü Düzeyi",
            items: [
                { code: "2210", name: "Yurt İçi Yüksek Lisans Burs Programları" },
                { code: "2211", name: "Yurt İçi Doktora Burs Programları" },
                { code: "2213-A", name: "Yurt Dışı Doktora Burs Programı" },
                { code: "2213-B", name: "Yurt Dışı Müşterek Doktora Burs Programı" },
                { code: "2244", name: "Sanayi Doktora Programı" },
                { code: "2250", name: "Lisansüstü Bursları Performans Programı" },
                { code: "2214-A", name: "Yurt Dışı Doktora Sırası Araştırma Burs Programı" },
                { code: "2236-B", name: "MSCA-COFUND Burs Programlarına Katkı Fonu Programı" },
                { code: "TWAS", name: "Gelişmekte Olan Dünya için Bilimler Akademisi Bursları" },
                { code: "2216C", name: "TÜBA-TÜBİTAK Özbekistan Aziz Sancar Araştırma Burs Programı" },
                { code: "ICGEB", name: "Uluslararası Gen Mühendisliği ve Biyoteknoloji Araştırma Merkezi Bursları" },
                { code: "2216", name: "Uluslararası Araştırmacılar İçin Araştırma Burs Programı" },
                { code: "EMBO", name: "Avrupa Moleküler Biyoloji Örgütü Destekleri" },
                { code: "2216B", name: "TÜBİTAK-TWAS Doktora Sırası ve Doktora Sonrası Araştırma Burs Programları" },
                { code: "2216D", name: "TÜBİTAK-WAITRO Doktora Sırası ve Doktora Sonrası Burs Programları" },
                { code: "ProfSezgin", name: "Prof. Dr. Fuat Sezgin Bursları" },
                { code: "BİÇABA", name: "Birlikte Çalışıp Birlikte Başaracağız Burs Programı" }
            ]
        },
        {
            category: "Doktora Sonrası Düzeyi",
            items: [
                { code: "2218", name: "Yurt İçi Doktora Sonrası Araştırma Burs Programı" },
                { code: "2219", name: "Yurt Dışı Doktora Sonrası Araştırma Burs Programı" },
                { code: "2221", name: "Konuk veya Akademik İzinli (Sabbatical) Bilim İnsanı Destekleme Programı" },
                { code: "2247-A", name: "Ulusal Lider Araştırmacılar Programı" },
                { code: "2232-A", name: "Uluslararası Lider Araştırmacılar Programı" },
                { code: "2236-A", name: "Uluslararası Deneyimli Araştırmacı Dolaşımı Destek Programı" },
                { code: "2247-B", name: "ERC Projeleri Güçlendirme Desteği Programı" },
                { code: "2219-S", name: "Aziz Sancar Yurt Dışı Doktora Sonrası Araştırma Burs Programı" },
                { code: "2247-D", name: "Ulusal Genç Liderler Programı" },
                { code: "2232-B", name: "Uluslararası Genç Araştırmacılar Programı" },
                { code: "ProfSezgin", name: "Prof. Dr. Fuat Sezgin Bursları" },
                { code: "EMBO", name: "Avrupa Moleküler Biyoloji Örgütü Destekleri" },
                { code: "2216C", name: "TÜBA-TÜBİTAK Özbekistan Aziz Sancar Araştırma Burs Programı" },
                { code: "ICGEB", name: "Uluslararası Gen Mühendisliği ve Biyoteknoloji Araştırma Merkezi Bursları" }
            ]
        }
    ];

    if (loading) {
        return <div className="loading-container">Yükleniyor...</div>;
    }

    return (
        <div className="App">
            <button className="hamburger" onClick={toggleSidebar}>☰</button>

            <div className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
                {/* Üst sabit bölüm: Logo ve Yeni Sohbet */}
                <div className="sidebar-header">
                    <div className="upperSideTop">
                        <img src={chatLogo} alt="Logo" className="logo" />
                        <span className="brand">TUBITAK Chat</span>
                    </div>

                    <button className="midBtn" onClick={startNewChatSession}>
                        <img src={addBtn} alt="" className="addbtn" />
                        Yeni Sohbet
                    </button>
                </div>

                {/* Orta kaydırılabilir bölüm */}
                <div className="sidebar-scrollable">
                    {/* Hata mesajları */}
                    {apiError && <div className="alert api"><strong>API Uyarısı:</strong> {apiError}</div>}
                    {serverError && (
                        <div className="alert server">
                            <strong>Sunucu Hatası:</strong> {serverError}
                            <div className="resetBtn">
                                <button onClick={handleResetApp}>Sohbeti Sıfırla</button>
                            </div>
                        </div>
                    )}

                    {/* AI Model Seçimi */}
                    <div className="sidebar-section modelSelect">
                        <h3 className="section-title">AI Modeli Seçin:</h3>
                        <div className="model-buttons">
                            <button
                                className={aiModel === 'openai' ? 'active' : ''}
                                onClick={() => changeAiModel('openai')}
                                disabled={modelLoading}
                            >
                                OpenAI
                            </button>
                            <button
                                className={aiModel === 'lstm' ? 'active' : ''}
                                onClick={() => changeAiModel('lstm')}
                                disabled={modelLoading}
                            >
                                LSTM
                            </button>
                        </div>
                    </div>

                    {/* Sohbet Geçmişi */}
                    <div className="sidebar-section chatHistoryContainer">
                        <h3 className="section-title">Sohbet Geçmişi</h3>
                        <div className="chatHistoryScroll">
                            {historyLoading ? (
                                <div className="historyLoading">Yükleniyor...</div>
                            ) : chatHistory.length === 0 ? (
                                <div className="historyEmpty">Henüz sohbet geçmişi yok</div>
                            ) : (
                                chatHistory.map(session => (
                                    <div
                                        key={session.id}
                                        className={`historyItem ${currentSession?.id === session.id ? 'active' : ''}`}
                                        onClick={() => loadChatSession(session.id)}
                                    >
                                        <span className="historyIcon">💬</span>
                                        <div className="historyContent">
                                            <span className="historyText">
                                                {/* Benzer başlıklı sohbetleri ayırt etmek için ID ekle */}
                                                {session.title || "Yeni Sohbet"}
                                                {/* Başlıklar aynıysa ID'lerini de göster */}
                                                {chatHistory.filter(s => s.title === session.title).length > 1 &&
                                                    ` #${session.id.toString().substring(session.id.toString().length - 3)}`}
                                            </span>
                                            {session.created_at && (
                                                <span className="historyTime">
                                                    {getTimeAgo(session.created_at)}
                                                </span>
                                            )}
                                        </div>
                                        <button
                                            className="historyDelete"
                                            onClick={(e) => handleDeleteSession(session.id, e)}
                                            title="Sohbeti sil"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </div>

                {/* Alt sabit bölüm: Profil ve Çıkış Yap */}
                <div className="sidebar-footer">
                    <div className="navigationLinks">
                        <button className="nav-link" onClick={() => navigate('/calendar')}>
                            <span className="nav-icon">📅</span>
                            <span className="nav-text">Takvim</span>
                        </button>
                        <button className="nav-link" onClick={() => navigate('/profile')}>
                            <Avatar src={user?.profile?.profile_picture} size={20} className="nav-avatar" />
                            <span className="nav-text">Profilim</span>
                        </button>
                    </div>
                    <button className="logout-btn" onClick={logoutUser}>
                        <img src={rocket} alt="Logout" className="logout-icon" />
                        <span>Çıkış Yap</span>
                    </button>
                </div>
            </div>

            <div className="main" style={{ marginLeft: isSidebarOpen ? '320px' : '0' }}>
                <div className="chats">
                    {chats.map((chat, index) => (
                        <div key={index} className={`chat ${chat.sender === "bot" ? "bot" : ""}`}>
                            {chat.sender === "bot" ? (
                                <img className="chatimg" src={imgLogo} alt="bot" />
                            ) : (
                                <Avatar
                                    src={user?.profile?.profile_picture ?
                                        `http://localhost:8000${user.profile.profile_picture}` :
                                        undefined}
                                    size={40}
                                    alt="user avatar"
                                    className="chatimg"
                                />
                            )}

                            {chat.type === "fonSecimi" ? (
                                <div className="fon-cards">
                                    {fonlar.map((kategori, kIdx) => (
                                        <div key={kIdx} className="fon-kategori">
                                            <h3 className="fon-kategori-baslik">{kategori.category}</h3>
                                            <div className="fon-kategori-listesi">
                                                {kategori.items.map((fon, fIdx) => (
                                                    <div
                                                        key={fIdx}
                                                        className={`fon-card ${selectedFon === fon.code ? 'selected' : ''}`}
                                                        onClick={() => handleFonSelect(fon.code)}
                                                    >
                                                        <strong>{fon.code}</strong>
                                                        <p>{fon.name}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="message-container">
                                    <p className="txt">{chat.text}</p>

                                    {/* Bot mesajı için ekstra bileşenler */}
                                    {chat.sender === "bot" && (
                                        <>
                                            {/* Plan mesajı mı kontrol et ve takvim oluşturma butonu ekle */}
                                            {isPlanMessage(chat.text) && (
                                                <div className="takvim-secenegi">
                                                    {!chat.calendarCreated ? (
                                                        <button
                                                            className="takvim-olustur-btn"
                                                            onClick={() => handleCreateCalendar(chat.text, chat.id)}
                                                        >
                                                            Bu plan için takvim oluştur
                                                        </button>
                                                    ) : (
                                                        <div className="takvim-butonlari">
                                                            <button
                                                                className="takvim-goster-btn"
                                                                onClick={() => navigate('/calendar')}
                                                            >
                                                                Takvimi görüntüle
                                                            </button>
                                                            <button
                                                                className="takvim-indir-btn"
                                                                onClick={() => {
                                                                    const calendarId = Object.keys(projectCalendars).find(
                                                                        id => projectCalendars[id].sourceChatId === chat.id
                                                                    );
                                                                    if (calendarId) {
                                                                        handleDownloadCalendar(calendarId);
                                                                    } else {
                                                                        alert("Bu mesaj için takvim bulunamadı!");
                                                                    }
                                                                }}
                                                            >
                                                                Takvimi bilgisayarına indir (.ics)
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Geri bildirim bölümü */}
                                            <div className="feedback-section">
                                                {!showFeedback[chat.id] ? (
                                                    <button
                                                        className="feedback-button"
                                                        onClick={() => toggleFeedback(chat.id)}
                                                    >
                                                        Bu cevap işinize yaradı mı?
                                                    </button>
                                                ) : (
                                                    <div className="feedback-form">
                                                        <h4>Bu cevap işinize yaradı mı?</h4>
                                                        <div className="star-rating">
                                                            {[1, 2, 3, 4, 5].map((star) => (
                                                                <span
                                                                    key={star}
                                                                    className="star"
                                                                    onClick={() => submitFeedback(chat.id, star)}
                                                                    role="button"
                                                                    title={`${star} yıldız`}
                                                                    disabled={submittingFeedback}
                                                                >
                                                                    ★
                                                                </span>
                                                            ))}
                                                        </div>
                                                        <textarea
                                                            placeholder="İsteğe bağlı yorum ekleyin..."
                                                            value={feedbackComment}
                                                            onChange={(e) => setFeedbackComment(e.target.value)}
                                                            disabled={submittingFeedback}
                                                        />
                                                        <div className="feedback-buttons">
                                                            <button
                                                                onClick={() => toggleFeedback(chat.id)}
                                                                disabled={submittingFeedback}
                                                            >
                                                                İptal
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}

                    {isLoading && (
                        <div className="chat bot">
                            <img className="chatimg" src={imgLogo} alt="bot" />
                            <p className="txt">
                                <span className="loading-dots">
                                    {loadingText}<span>.</span><span>.</span><span>.</span>
                                </span>
                            </p>
                        </div>
                    )}

                    {/* Auto-scroll için referans elementi */}
                    <div ref={chatEndRef} />
                </div>

                <div className="chatFooter">
                    <div className="inp">
                        <input
                            type="text"
                            placeholder="Mesaj gönderin"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                            disabled={isLoading}
                        />
                        <button
                            className={`send ${isLoading ? 'disabled' : ''}`}
                            onClick={handleSend}
                            disabled={isLoading}
                        >
                            <img src={sendBtn} alt="Send" />
                        </button>
                    </div>
                    <p>
                        {aiModel === 'openai'
                            ? 'OpenAI ile çalışıyor'
                            : 'TÜBİTAK LSTM AI ile çalışıyor'}
                    </p>
                </div>
            </div>
        </div>
    );
};

export default MainChatApp;