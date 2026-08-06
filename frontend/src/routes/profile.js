import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getProjects, downloadSessionDoc } from '../endpoints/api';
import { useNavigate } from 'react-router-dom';

function Profile() {
    const { user, updateProfile, uploadProfilePicture, logoutUser } = useAuth();
    const [profileImage, setProfileImage] = useState(null);
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        bio: ''
    });
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [downloadingDoc, setDownloadingDoc] = useState(false);
    const [currentDownloadingProject, setCurrentDownloadingProject] = useState(null);
    const [userDocs, setUserDocs] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        if (user) {
            setFormData({
                first_name: user.first_name || '',
                last_name: user.last_name || '',
                email: user.email || '',
                bio: user.bio || ''
            });
            loadProjects();
            loadDownloadedDocs();
        }
    }, [user]);

    const loadProjects = async () => {
        try {
            const data = await getProjects();
            // Tarih ve süre hesaplamaları ekle
            const projectsWithTime = data.map(project => {
                // created_at varsa işle
                if (project.created_at) {
                    const createdDate = new Date(project.created_at);
                    const now = new Date();
                    const diffMs = now - createdDate;

                    // Saat ve dakika hesapla
                    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

                    // Süre metni oluştur
                    let timeAgo = '';
                    if (diffHours > 0) {
                        timeAgo = `${diffHours} saat ${diffMinutes} dakika önce`;
                    } else {
                        timeAgo = `${diffMinutes} dakika önce`;
                    }

                    return {
                        ...project,
                        timeAgo: timeAgo
                    };
                }
                return {
                    ...project,
                    timeAgo: 'Bilinmiyor'
                };
            });

            setProjects(projectsWithTime);
            setLoading(false);
        } catch (error) {
            console.error('Projeler yüklenemedi:', error);
            setLoading(false);
        }
    };

    // İndirilen DOC'ları yükle
    const loadDownloadedDocs = () => {
        try {
            // Yerel depolamadan indirilen belgeleri al
            const docsKey = `downloadedDocs_${user.id}`;
            const savedDocs = localStorage.getItem(docsKey);

            if (savedDocs) {
                const parsedDocs = JSON.parse(savedDocs);
                setUserDocs(parsedDocs);
                console.log("İndirilen DOC'lar yüklendi:", parsedDocs);
            }
        } catch (error) {
            console.error('İndirilen DOC bilgileri yüklenemedi:', error);
        }
    };

    // AI model adını düzgün göster
    const getModelName = (modelCode) => {
        const modelMap = {
            'openai': 'OpenAI GPT',
            'lstm': 'TÜBİTAK LSTM',
            'gemini': 'Google Gemini',
            'custom_lstm': 'TÜBİTAK LSTM'
        };

        return modelMap[modelCode] || modelCode;
    };

    // Modele göre renk belirle
    const getModelBadgeColor = (modelCode) => {
        const colorMap = {
            'openai': '#10a37f',  // OpenAI yeşili
            'lstm': '#004b93',    // TÜBİTAK mavisi
            'gemini': '#8e44ad',  // Gemini için mor
            'custom_lstm': '#004b93'  // TÜBİTAK mavisi
        };

        return colorMap[modelCode] || '#666';
    };

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleImageChange = (e) => {
        if (e.target.files && e.target.files[0]) setProfileImage(e.target.files[0]);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await updateProfile(formData);
            if (profileImage) await uploadProfilePicture(profileImage);
            alert('Profil başarıyla güncellendi!');
        } catch (error) {
            console.error('Profil güncellenemedi:', error);
            alert('Profil güncellenirken bir hata oluştu.');
        }
    };

    // DOC indirme - Bu kısım önemli!
    const handleDocDownload = async (sessionId) => {
        setDownloadingDoc(true);
        setCurrentDownloadingProject(sessionId);

        try {
            // İlgili projeyi bul
            const project = projects.find(p => p.id === sessionId);
            if (!project) {
                throw new Error("Proje bulunamadı");
            }

            // DOC'u indir
            await downloadSessionDoc(sessionId);

            // İndirme bilgisini kaydet
            const docInfo = {
                id: Date.now().toString(),
                projectId: sessionId,
                title: project.title || "İsimsiz Proje",
                downloadDate: new Date().toISOString(),
                ai_model_used: project.ai_model_used || "unknown",
                duration_months: project.duration_months || 0
            };

            // Mevcut indirilen DOC'ları al
            const docsKey = `downloadedDocs_${user.id}`;
            let downloadedDocs = [];
            const savedDocs = localStorage.getItem(docsKey);

            if (savedDocs) {
                downloadedDocs = JSON.parse(savedDocs);
            }

            // Bu DOC zaten indirilmiş mi kontrol et
            const existingIndex = downloadedDocs.findIndex(doc => doc.projectId === sessionId);

            if (existingIndex >= 0) {
                // Eğer zaten indirilmişse, bilgileri güncelle
                downloadedDocs[existingIndex] = {
                    ...downloadedDocs[existingIndex],
                    downloadDate: docInfo.downloadDate
                };
            } else {
                // Yeni indirilen DOC'u ekle
                downloadedDocs.push(docInfo);
            }

            // Güncel listeyi kaydet
            localStorage.setItem(docsKey, JSON.stringify(downloadedDocs));

            // State'i güncelle
            setUserDocs(downloadedDocs);

            alert("DOC başarıyla indirildi!");
            return true;
        } catch (error) {
            console.error('DOCX indirme hatası:', error);
            alert('DOCX indirilirken bir hata oluştu: ' + error.message);
            return false;
        } finally {
            setDownloadingDoc(false);
            setCurrentDownloadingProject(null);
        }
    };

    // DOC'u yeniden indir
    const handleRedownloadDoc = async (projectId) => {
        await handleDocDownload(projectId);
    };

    if (!user) return <div>Yükleniyor...</div>;

    return (
        <div style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto', fontFamily: 'Poppins, sans-serif' }}>
            {/* ÜST BAR */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
                <h1 style={{ color: '#e30613', fontSize: '28px' }}>Profil Sayfası</h1>
                <div>
                    <button onClick={() => navigate('/')} style={{ padding: '10px 20px', backgroundColor: '#444', color: '#fff', border: 'none', borderRadius: '5px', marginRight: '10px', cursor: 'pointer' }}>
                        Ana Sayfa
                    </button>
                    <button onClick={logoutUser} style={{ padding: '10px 20px', backgroundColor: '#e30613', color: '#fff', border: 'none', borderRadius: '5px', cursor: 'pointer' }}>
                        Çıkış Yap
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '30px', flexWrap: 'wrap' }}>
                {/* ---- PROFİL BİLGİLERİ ---- */}
                <div style={{ flex: '1', minWidth: '300px' }}>
                    <div style={{ backgroundColor: '#fff', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
                        <h2 style={{ marginBottom: '20px', color: '#333', fontSize: '20px' }}>Hesap Bilgileri</h2>
                        {/* Avatar */}
                        <div style={{ textAlign: 'center', marginBottom: '20px' }}>
                            <div style={{ width: '100px', height: '100px', margin: '0 auto', borderRadius: '50%', overflow: 'hidden', border: '3px solid #e30613' }}>
                                <img src={user.profile_picture || 'https://placehold.co/100x100'} alt={user.username} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                            </div>
                            <p style={{ marginTop: '10px', fontWeight: 'bold', fontSize: '18px' }}>{user.username}</p>
                        </div>
                        {/* Form */}
                        <form onSubmit={handleSubmit}>
                            {/* tek tek inputlar */}
                            {['first_name', 'last_name', 'email'].map((field) => (
                                <div key={field} style={{ marginBottom: '15px' }}>
                                    <label style={{ display: 'block', marginBottom: '5px', color: '#555' }}>{field === 'first_name' ? 'Ad' : field === 'last_name' ? 'Soyad' : 'E‑posta'}</label>
                                    <input type={field === 'email' ? 'email' : 'text'} name={field} value={formData[field]} onChange={handleChange} style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ddd' }} />
                                </div>
                            ))}
                            {/* Bio */}
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', color: '#555' }}>Hakkımda</label>
                                <textarea name="bio" value={formData.bio} onChange={handleChange} style={{ width: '100%', padding: '10px', borderRadius: '5px', border: '1px solid #ddd', minHeight: '100px' }} />
                            </div>
                            {/* Profil resmi */}
                            <div style={{ marginBottom: '15px' }}>
                                <label style={{ display: 'block', marginBottom: '5px', color: '#555' }}>Profil Resmi</label>
                                <input type="file" onChange={handleImageChange} style={{ width: '100%' }} />
                            </div>
                            <button type="submit" style={{ padding: '10px 20px', backgroundColor: '#e30613', color: '#fff', border: 'none', borderRadius: '5px', width: '100%', cursor: 'pointer', fontSize: '16px' }}>
                                Profili Güncelle
                            </button>
                        </form>
                    </div>
                </div>

                {/* ---- PROJELER / PLANLAR ---- */}
                <div style={{ flex: '1.5', minWidth: '300px' }}>
                    <div style={{ backgroundColor: '#fff', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '30px' }}>
                        <h2 style={{ marginBottom: '20px', color: '#333', fontSize: '20px' }}>Projelerim</h2>
                        {loading ? (
                            <p>Projeler yükleniyor...</p>
                        ) : projects.length === 0 ? (
                            <p>Henüz projeniz bulunmuyor.</p>
                        ) : (
                            <div>
                                {projects.map((project) => (
                                    <div key={project.id} className="plan-card" style={{ padding: '15px', borderBottom: '1px solid #eee', marginBottom: '15px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '5px' }}>
                                            <h3 style={{ fontSize: '18px', color: '#333', margin: 0 }}>{project.title}</h3>
                                            <span style={{ fontSize: '12px', color: '#888' }}>{project.timeAgo}</span>
                                        </div>
                                        <p style={{ color: '#666', margin: '10px 0' }}>{project.description}</p>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <div>
                                                <span style={{
                                                    display: 'inline-block',
                                                    padding: '3px 8px',
                                                    borderRadius: '4px',
                                                    backgroundColor: getModelBadgeColor(project.ai_model_used),
                                                    color: '#fff',
                                                    fontSize: '12px',
                                                    marginRight: '8px'
                                                }}>
                                                    {getModelName(project.ai_model_used)}
                                                </span>
                                                <span style={{ color: '#666', fontSize: '14px' }}> Süre: {project.duration_months} ay</span>
                                            </div>
                                            <button
                                                onClick={() => handleDocDownload(project.id)}
                                                disabled={downloadingDoc}
                                                style={{
                                                    backgroundColor: downloadingDoc && currentDownloadingProject === project.id ? '#999' : '#e30613',
                                                    color: '#fff',
                                                    border: 'none',
                                                    borderRadius: '5px',
                                                    padding: '5px 10px',
                                                    cursor: downloadingDoc && currentDownloadingProject === project.id ? 'default' : 'pointer',
                                                    fontSize: '14px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '5px'
                                                }}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                                                    <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z" />
                                                    <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z" />
                                                </svg>
                                                {downloadingDoc && currentDownloadingProject === project.id ? 'İndiriliyor…' : 'DOC İndir'}
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* ---- İNDİRİLEN DOC DOSYALARI ---- */}
                    <div style={{ backgroundColor: '#fff', padding: '25px', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
                        <h2 style={{ marginBottom: '20px', color: '#333', fontSize: '20px' }}>İndirilen DOC Dosyaları</h2>
                        {userDocs.length === 0 ? (
                            <div>
                                <p>Henüz indirilen DOC dosyanız bulunmuyor.</p>
                                <p style={{ fontSize: '14px', color: '#666', marginTop: '10px' }}>
                                    Projelerinizden DOC dosyası indirerek burada görüntüleyebilirsiniz.
                                </p>
                            </div>
                        ) : (
                            <div>
                                {userDocs.map((doc) => (
                                    <div key={doc.id} className="doc-card" style={{ padding: '15px', borderBottom: '1px solid #eee', marginBottom: '15px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '5px' }}>
                                            <h3 style={{ fontSize: '18px', color: '#333', margin: 0 }}>{doc.title}</h3>
                                            <span style={{ fontSize: '12px', color: '#888' }}>
                                                {new Date(doc.downloadDate).toLocaleDateString('tr-TR', {
                                                    year: 'numeric',
                                                    month: 'long',
                                                    day: 'numeric',
                                                    hour: '2-digit',
                                                    minute: '2-digit'
                                                })}
                                            </span>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                                            <div>
                                                <span style={{
                                                    display: 'inline-block',
                                                    padding: '3px 8px',
                                                    borderRadius: '4px',
                                                    backgroundColor: getModelBadgeColor(doc.ai_model_used),
                                                    color: '#fff',
                                                    fontSize: '12px',
                                                    marginRight: '8px'
                                                }}>
                                                    {getModelName(doc.ai_model_used)}
                                                </span>
                                                {doc.duration_months && (
                                                    <span style={{ color: '#666', fontSize: '14px' }}> Süre: {doc.duration_months} ay</span>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => handleRedownloadDoc(doc.projectId)}
                                                disabled={downloadingDoc}
                                                style={{
                                                    backgroundColor: downloadingDoc ? '#999' : '#004b93',
                                                    color: '#fff',
                                                    border: 'none',
                                                    borderRadius: '5px',
                                                    padding: '5px 10px',
                                                    cursor: downloadingDoc ? 'default' : 'pointer',
                                                    fontSize: '14px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '5px'
                                                }}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                                                    <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z" />
                                                    <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z" />
                                                </svg>
                                                Yeniden İndir
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default Profile;