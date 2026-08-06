import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import chatLogo from '../assets/chatgpt.svg';

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { user, loginUser } = useAuth();
    const navigate = useNavigate();

    // Kullanıcı zaten giriş yapmışsa ana sayfaya yönlendir
    useEffect(() => {
        if (user) {
            navigate('/');
        }
    }, [user, navigate]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!username.trim()) {
            setError('Kullanıcı adı gereklidir');
            return;
        }

        if (!password) {
            setError('Şifre gereklidir');
            return;
        }

        setError('');
        setIsLoading(true);

        try {
            const success = await loginUser(username, password);
            if (success) {
                if (rememberMe) {
                    localStorage.setItem('remembered_username', username);
                } else {
                    localStorage.removeItem('remembered_username');
                }
                navigate('/');
            } else {
                setError('Giriş başarısız. Lütfen kullanıcı adı ve şifrenizi kontrol edin.');
            }
        } catch (err) {
            setError('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
            console.error('Login error:', err);
        } finally {
            setIsLoading(false);
        }
    };

    // Hatırlanmış kullanıcı adını al
    useEffect(() => {
        const rememberedUsername = localStorage.getItem('remembered_username');
        if (rememberedUsername) {
            setUsername(rememberedUsername);
            setRememberMe(true);
        }
    }, []);

    return (
        <div className="login-container" style={styles.container}>
            <div style={styles.loginBox}>
                <div style={styles.logoContainer}>
                    <img src={chatLogo} alt="TÜBİTAK Chat Logo" style={styles.logo} />
                    <h1 style={styles.title}>TÜBİTAK Chat</h1>
                </div>

                <h2 style={styles.subtitle}>Giriş Yap</h2>

                {error && <div style={styles.error}>{error}</div>}

                <form onSubmit={handleSubmit} style={styles.form}>
                    <div style={styles.inputGroup}>
                        <label htmlFor="username" style={styles.label}>Kullanıcı Adı</label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            style={styles.input}
                            placeholder="Kullanıcı adınızı girin"
                            disabled={isLoading}
                        />
                    </div>

                    <div style={styles.inputGroup}>
                        <label htmlFor="password" style={styles.label}>Şifre</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={styles.input}
                            placeholder="Şifrenizi girin"
                            disabled={isLoading}
                        />
                    </div>

                    <div style={styles.checkboxContainer}>
                        <label style={styles.rememberMeLabel}>
                            <input
                                type="checkbox"
                                checked={rememberMe}
                                onChange={(e) => setRememberMe(e.target.checked)}
                                style={styles.checkbox}
                                disabled={isLoading}
                            />
                            <span style={styles.checkboxText}>Beni hatırla</span>
                        </label>
                    </div>

                    <button
                        type="submit"
                        style={isLoading ? { ...styles.button, ...styles.buttonDisabled } : styles.button}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Giriş Yapılıyor...' : 'Giriş Yap'}
                    </button>

                    <div style={styles.links}>
                        <Link to="/register" style={styles.link}>Hesap oluştur</Link>
                        <span style={styles.separator}>|</span>
                        <Link to="/forgot-password" style={styles.link}>Şifremi unuttum</Link>
                    </div>
                </form>
            </div>

            <div style={styles.footer}>
                <p>TÜBİTAK - 2024 © Tüm Hakları Saklıdır</p>
                <div style={styles.footerLinks}>
                    <a href="https://www.tubitak.gov.tr/" target="_blank" rel="noopener noreferrer" style={styles.footerLink}>
                        TÜBİTAK Anasayfa
                    </a>
                    <a href="https://www.tubitak.gov.tr/tr/destekler" target="_blank" rel="noopener noreferrer" style={styles.footerLink}>
                        Destek Programları
                    </a>
                    <Link to="/help" style={styles.footerLink}>Yardım</Link>
                </div>
            </div>
        </div>
    );
};

// Stiller
const styles = {
    container: {
        display: 'flex',
        flexDirection: 'column',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%)',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        fontFamily: '"Poppins", sans-serif',
    },
    loginBox: {
        width: '100%',
        maxWidth: '450px',
        backgroundColor: '#fff',
        borderRadius: '10px',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.1)',
        padding: '30px',
        marginBottom: '30px',
    },
    logoContainer: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: '30px',
    },
    logo: {
        width: '50px',
        height: '50px',
        marginRight: '10px',
    },
    title: {
        color: '#e30613',
        fontSize: '2.4rem',
        margin: 0,
        fontWeight: '700',
    },
    subtitle: {
        textAlign: 'center',
        color: '#333',
        fontSize: '1.8rem',
        marginBottom: '25px',
        fontWeight: '600',
    },
    form: {
        width: '100%',
    },
    inputGroup: {
        marginBottom: '20px',
    },
    label: {
        display: 'block',
        marginBottom: '8px',
        fontSize: '1.4rem',
        color: '#555',
        fontWeight: '500',
    },
    input: {
        width: '100%',
        padding: '12px 15px',
        fontSize: '1.4rem',
        border: '1px solid #ddd',
        borderRadius: '5px',
        backgroundColor: '#f9f9f9',
        transition: 'border-color 0.3s, box-shadow 0.3s',
        outline: 'none',
    },
    error: {
        backgroundColor: '#ffebee',
        color: '#e30613',
        padding: '10px 15px',
        borderRadius: '5px',
        marginBottom: '20px',
        fontSize: '1.4rem',
        textAlign: 'center',
    },
    checkboxContainer: {
        marginBottom: '25px',
    },
    rememberMeLabel: {
        display: 'flex',
        alignItems: 'center',
        cursor: 'pointer',
    },
    checkbox: {
        marginRight: '10px',
        cursor: 'pointer',
    },
    checkboxText: {
        fontSize: '1.4rem',
        color: '#555',
    },
    button: {
        width: '100%',
        padding: '12px',
        backgroundColor: '#e30613',
        color: 'white',
        border: 'none',
        borderRadius: '5px',
        fontSize: '1.6rem',
        fontWeight: '500',
        cursor: 'pointer',
        transition: 'background-color 0.2s',
        marginBottom: '20px',
    },
    buttonDisabled: {
        backgroundColor: '#f2a1a6',
        cursor: 'not-allowed',
    },
    links: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        fontSize: '1.4rem',
    },
    link: {
        color: '#e30613',
        textDecoration: 'none',
        transition: 'color 0.2s',
    },
    separator: {
        margin: '0 10px',
        color: '#aaa',
    },
    footer: {
        textAlign: 'center',
        color: '#666',
        fontSize: '1.2rem',
    },
    footerLinks: {
        display: 'flex',
        justifyContent: 'center',
        gap: '20px',
        marginTop: '10px',
    },
    footerLink: {
        color: '#666',
        textDecoration: 'none',
    },
};

export default Login;