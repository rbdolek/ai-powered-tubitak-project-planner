import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import chatLogo from '../assets/chatgpt.svg';

const Register = () => {
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        firstName: '',
        lastName: '',
        agreeToTerms: false,
    });

    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const { user, registerUser } = useAuth();
    const navigate = useNavigate();

    // Kullanıcı zaten giriş yapmışsa ana sayfaya yönlendir
    useEffect(() => {
        if (user) {
            navigate('/');
        }
    }, [user, navigate]);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData({
            ...formData,
            [name]: type === 'checkbox' ? checked : value,
        });
    };

    const validateForm = () => {
        // Kullanıcı adı kontrolü
        if (!formData.username.trim()) {
            setError('Kullanıcı adı gereklidir');
            return false;
        }

        if (formData.username.length < 4) {
            setError('Kullanıcı adı en az 4 karakter olmalıdır');
            return false;
        }

        // E-posta kontrolü
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(formData.email)) {
            setError('Geçerli bir e-posta adresi girin');
            return false;
        }

        // Şifre kontrolü
        if (formData.password.length < 8) {
            setError('Şifre en az 8 karakter olmalıdır');
            return false;
        }

        // Şifre eşleşme kontrolü
        if (formData.password !== formData.confirmPassword) {
            setError('Şifreler eşleşmiyor');
            return false;
        }

        // Şartlar ve koşullar onayı
        if (!formData.agreeToTerms) {
            setError('Şartlar ve koşulları kabul etmelisiniz');
            return false;
        }

        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        setError('');
        setSuccessMessage('');
        setIsLoading(true);

        try {
            const userData = {
                username: formData.username,
                email: formData.email,
                password: formData.password,
                first_name: formData.firstName, // snake_case'e dikkat et
                last_name: formData.lastName    // snake_case'e dikkat et
            };

            const user = await registerUser(userData);

            if (user) {
                setSuccessMessage('Kaydınız başarıyla oluşturuldu! Yönetici onayından sonra giriş yapabilirsiniz.');
                // Form alanlarını temizle
                setFormData({
                    username: '',
                    email: '',
                    password: '',
                    confirmPassword: '',
                    firstName: '',
                    lastName: '',
                    agreeToTerms: false,
                });

                // 3 saniye sonra login sayfasına yönlendir
                setTimeout(() => {
                    navigate('/login');
                }, 3000);
            } else {
                setError('Kayıt oluşturulamadı. Lütfen tekrar deneyin.');
            }
        } catch (err) {
            setError('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.');
            console.error('Register error:', err);
        } finally {
            setIsLoading(false);
        }
    };


    return (
        <div className="register-container" style={styles.container}>
            <div style={styles.registerBox}>
                <div style={styles.logoContainer}>
                    <img src={chatLogo} alt="TÜBİTAK Chat Logo" style={styles.logo} />
                    <h1 style={styles.title}>TÜBİTAK Chat</h1>
                </div>

                <h2 style={styles.subtitle}>Hesap Oluştur</h2>

                {error && <div style={styles.error}>{error}</div>}
                {successMessage && <div style={styles.success}>{successMessage}</div>}

                <form onSubmit={handleSubmit} style={styles.form}>
                    <div style={styles.formColumns}>
                        <div style={styles.formColumn}>
                            <div style={styles.inputGroup}>
                                <label htmlFor="username" style={styles.label}>Kullanıcı Adı <span style={styles.required}>*</span></label>
                                <input
                                    type="text"
                                    id="username"
                                    name="username"
                                    value={formData.username}
                                    onChange={handleChange}
                                    style={styles.input}
                                    placeholder="Kullanıcı adınızı girin"
                                    disabled={isLoading}
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label htmlFor="email" style={styles.label}>E-posta <span style={styles.required}>*</span></label>
                                <input
                                    type="email"
                                    id="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    style={styles.input}
                                    placeholder="E-posta adresinizi girin"
                                    disabled={isLoading}
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label htmlFor="firstName" style={styles.label}>Ad</label>
                                <input
                                    type="text"
                                    id="firstName"
                                    name="firstName"
                                    value={formData.firstName}
                                    onChange={handleChange}
                                    style={styles.input}
                                    placeholder="Adınızı girin"
                                    disabled={isLoading}
                                />
                            </div>
                        </div>

                        <div style={styles.formColumn}>
                            <div style={styles.inputGroup}>
                                <label htmlFor="password" style={styles.label}>Şifre <span style={styles.required}>*</span></label>
                                <input
                                    type="password"
                                    id="password"
                                    name="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    style={styles.input}
                                    placeholder="Şifrenizi girin (en az 8 karakter)"
                                    disabled={isLoading}
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label htmlFor="confirmPassword" style={styles.label}>Şifre Tekrar <span style={styles.required}>*</span></label>
                                <input
                                    type="password"
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    style={styles.input}
                                    placeholder="Şifrenizi tekrar girin"
                                    disabled={isLoading}
                                    required
                                />
                            </div>

                            <div style={styles.inputGroup}>
                                <label htmlFor="lastName" style={styles.label}>Soyad</label>
                                <input
                                    type="text"
                                    id="lastName"
                                    name="lastName"
                                    value={formData.lastName}
                                    onChange={handleChange}
                                    style={styles.input}
                                    placeholder="Soyadınızı girin"
                                    disabled={isLoading}
                                />
                            </div>
                        </div>
                    </div>

                    <div style={styles.checkboxContainer}>
                        <label style={styles.termsLabel}>
                            <input
                                type="checkbox"
                                name="agreeToTerms"
                                checked={formData.agreeToTerms}
                                onChange={handleChange}
                                style={styles.checkbox}
                                disabled={isLoading}
                                required
                            />
                            <span style={styles.checkboxText}>
                                <a
                                    href="https://www.tubitak.gov.tr/tr/kurumsal/yasal-uyari"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={styles.termsLink}
                                >
                                    Şartlar ve koşulları
                                </a> kabul ediyorum
                            </span>
                        </label>
                    </div>

                    <button
                        type="submit"
                        style={isLoading ? { ...styles.button, ...styles.buttonDisabled } : styles.button}
                        disabled={isLoading}
                    >
                        {isLoading ? 'Kayıt Yapılıyor...' : 'Kayıt Ol'}
                    </button>

                    <div style={styles.loginLink}>
                        Zaten hesabınız var mı? <Link to="/login" style={styles.link}>Giriş Yap</Link>
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
    registerBox: {
        width: '100%',
        maxWidth: '800px',
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
    formColumns: {
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: '20px',
    },
    formColumn: {
        flex: '1 1 300px',
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
    required: {
        color: '#e30613',
        marginLeft: '3px',
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
    success: {
        backgroundColor: '#e8f5e9',
        color: '#2e7d32',
        padding: '10px 15px',
        borderRadius: '5px',
        marginBottom: '20px',
        fontSize: '1.4rem',
        textAlign: 'center',
    },
    checkboxContainer: {
        marginBottom: '25px',
    },
    termsLabel: {
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
    termsLink: {
        color: '#e30613',
        textDecoration: 'none',
        fontWeight: '500',
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
    loginLink: {
        textAlign: 'center',
        fontSize: '1.4rem',
        color: '#555',
    },
    link: {
        color: '#e30613',
        textDecoration: 'none',
        fontWeight: '500',
        transition: 'color 0.2s',
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

export default Register;