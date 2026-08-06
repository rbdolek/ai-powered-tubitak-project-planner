// LSTMModel.js
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    Button, Form, Select, Card, Alert, Spin, Input, Rate,
    Typography, Collapse, Divider, notification, Tabs, Tag,
    Timeline, Modal
} from 'antd';
import {
    DownloadOutlined,
    SendOutlined,
    RobotOutlined,
    LineChartOutlined,
    CheckCircleOutlined,
    InfoCircleOutlined,
    ThunderboltOutlined,
    QuestionCircleOutlined
} from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;
const { Title, Paragraph, Text } = Typography;
const { Panel } = Collapse;
const { TabPane } = Tabs;

const LSTMModel = () => {
    // State tanımları
    const [fonlar, setFonlar] = useState([]);
    const [selectedFon, setSelectedFon] = useState(null);
    const [selectedFonData, setSelectedFonData] = useState(null);
    const [userQuery, setUserQuery] = useState('');
    const [plan, setPlan] = useState(null);
    const [planId, setPlanId] = useState(null);
    const [metadata, setMetadata] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [feedbackScore, setFeedbackScore] = useState(0);
    const [feedbackSent, setFeedbackSent] = useState(false);
    const [infoModalVisible, setInfoModalVisible] = useState(false);

    // Fonları yükle
    useEffect(() => {
        axios.get('/api/fonlar/')
            .then(response => {
                setFonlar(response.data);
            })
            .catch(err => {
                setError('Fonlar yüklenirken bir hata oluştu.');
                console.error(err);
            });
    }, []);

    // Fon değişikliğinde çalışacak fonksiyon
    const handleFonChange = (value) => {
        setSelectedFon(value);

        // Seçilen fonun verilerini bul
        const fon = fonlar.find(f => f.id === value);
        setSelectedFonData(fon);

        // Fona göre varsayılan sorgu oluştur
        if (fon) {
            setUserQuery(`${fon.kod} kodlu ${fon.tur} fonu için ${fon.ay_suresi} aylık bir araştırma planı hazırlar mısın?`);
        }

        // Önceki plan ve geri bildirimi sıfırla
        setPlan(null);
        setPlanId(null);
        setMetadata(null);
        setFeedbackScore(0);
        setFeedbackSent(false);
    };

    // Sorgu değişikliğini izle
    const handleQueryChange = (e) => {
        setUserQuery(e.target.value);
    };

    // Plan oluştur
    const generatePlan = () => {
        if (!selectedFon) {
            notification.error({
                message: 'Fon Seçilmedi',
                description: 'Lütfen bir fon türü seçin.'
            });
            return;
        }

        setLoading(true);
        setError(null);
        setFeedbackSent(false);

        axios.post('/api/lstm_predict/', {
            fon_id: selectedFon,
            query: userQuery
        })
            .then(response => {
                if (response.data.success) {
                    setPlan(response.data.plan);
                    setPlanId(response.data.plan_id);
                    setMetadata(response.data.meta);

                    notification.success({
                        message: 'Plan Oluşturuldu',
                        description: 'Agent AI başarıyla planı oluşturdu. Planı inceleyebilir ve PDF olarak indirebilirsiniz.'
                    });
                } else {
                    setError(response.data.error || 'Bir hata oluştu.');
                    notification.error({
                        message: 'Hata',
                        description: response.data.error || 'Plan oluşturulurken bir hata meydana geldi.'
                    });
                }
                setLoading(false);
            })
            .catch(err => {
                setError('Plan oluşturulurken bir hata oluştu.');
                console.error(err);
                notification.error({
                    message: 'Hata',
                    description: 'Sunucuyla iletişim kurarken bir hata oluştu.'
                });
                setLoading(false);
            });
    };

    // PDF indir
    const downloadPDF = () => {
        if (planId) {
            window.open(`/api/generate_pdf/${planId}/`, '_blank');
        }
    };

    // Geri bildirim gönder
    const sendFeedback = () => {
        if (!planId || !feedbackScore) {
            notification.warning({
                message: 'Geri Bildirim Eksik',
                description: 'Lütfen planı puanlayın.'
            });
            return;
        }

        axios.post('/api/feedback/', {
            plan_id: planId,
            score: feedbackScore
        })
            .then(response => {
                if (response.data.success) {
                    setFeedbackSent(true);
                    notification.success({
                        message: 'Teşekkürler!',
                        description: 'Geri bildiriminiz için teşekkür ederiz. Bu geribildirim Agent AI\'ın gelişmesine katkı sağlayacak.'
                    });
                } else {
                    notification.error({
                        message: 'Hata',
                        description: response.data.error || 'Geri bildirim gönderilirken bir hata oluştu.'
                    });
                }
            })
            .catch(err => {
                console.error(err);
                notification.error({
                    message: 'Hata',
                    description: 'Sunucuyla iletişim kurarken bir hata oluştu.'
                });
            });
    };

    // Bilgi modalını göster
    const showInfoModal = () => {
        setInfoModalVisible(true);
    };

    // Bilgi modalını kapat
    const handleModalClose = () => {
        setInfoModalVisible(false);
    };

    // Fon özeti
    const renderFonSummary = () => {
        if (!selectedFonData) return null;

        return (
            <Card
                size="small"
                title={
                    <span>
                        <InfoCircleOutlined style={{ marginRight: 8 }} />
                        Seçilen Fon Bilgileri
                    </span>
                }
                style={{ marginBottom: 16 }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div>
                        <Text strong>Kod:</Text> <Text>{selectedFonData.kod}</Text>
                    </div>
                    <div>
                        <Text strong>Tür:</Text> <Text>{selectedFonData.tur}</Text>
                    </div>
                    <div>
                        <Text strong>Süre:</Text> <Text>{selectedFonData.ay_suresi} ay</Text>
                    </div>
                </div>
                {selectedFonData.aciklama && (
                    <div style={{ marginTop: 8 }}>
                        <Text strong>Açıklama:</Text> <Text>{selectedFonData.aciklama}</Text>
                    </div>
                )}
            </Card>
        );
    };

    // Plandaki araştırma adımlarını göster
    const renderResearchSteps = () => {
        if (!plan) return null;

        // Plan metninden adımları çıkarma
        const steps = [];
        const stepPattern = /(\d+)\.\s*ay:\s*(.+?)(?=\n|$)/g;
        let match;

        while ((match = stepPattern.exec(plan)) !== null) {
            steps.push({
                month: match[1],
                activity: match[2].trim()
            });
        }

        if (steps.length === 0) return null;

        return (
            <Card
                title={
                    <span>
                        <LineChartOutlined style={{ marginRight: 8 }} />
                        Araştırma Zaman Çizelgesi
                    </span>
                }
                style={{ marginTop: 16, marginBottom: 16 }}
            >
                <Timeline mode="left">
                    {steps.map((step, index) => (
                        <Timeline.Item
                            key={index}
                            label={`${step.month}. Ay`}
                            color={index === steps.length - 1 ? 'green' : 'blue'}
                        >
                            {step.activity}
                        </Timeline.Item>
                    ))}
                </Timeline>
            </Card>
        );
    };

    // Metadata'yı göster
    const renderMetadata = () => {
        if (!metadata) return null;

        return (
            <Collapse style={{ marginBottom: 16 }}>
                <Panel
                    header={
                        <span>
                            <ThunderboltOutlined style={{ marginRight: 8 }} />
                            Agent AI Metadata (Geliştiriciler İçin)
                        </span>
                    }
                    key="1"
                >
                    <pre style={{
                        backgroundColor: '#f5f5f5',
                        padding: 16,
                        borderRadius: 4,
                        overflow: 'auto'
                    }}>
                        {JSON.stringify(metadata, null, 2)}
                    </pre>
                </Panel>
            </Collapse>
        );
    };

    return (
        <div className="lstm-container" style={{ maxWidth: 800, margin: '0 auto', padding: 16 }}>
            <Card
                title={
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <RobotOutlined style={{ fontSize: 24, marginRight: 12, color: '#1890ff' }} />
                        <span>LSTM Agent AI ile Plan Oluştur</span>
                        <Button
                            type="link"
                            icon={<QuestionCircleOutlined />}
                            onClick={showInfoModal}
                            style={{ marginLeft: 'auto' }}
                        >
                            Nasıl Çalışır?
                        </Button>
                    </div>
                }
                bordered={true}
            >
                <Form layout="vertical">
                    <Form.Item
                        label="Fon Türü"
                        required
                        tooltip="Araştırma planı oluşturmak istediğiniz fonu seçin"
                    >
                        <Select
                            placeholder="TÜBİTAK fon programı seçin"
                            onChange={handleFonChange}
                            style={{ width: '100%' }}
                            showSearch
                            optionFilterProp="children"
                        >
                            {fonlar.map(fon => (
                                <Option key={fon.id} value={fon.id}>
                                    {fon.kod} - {fon.tur}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    {renderFonSummary()}

                    <Form.Item
                        label="Sorgu"
                        tooltip="Agent AI'a ne oluşturmasını istediğinizi detaylı olarak açıklayın"
                    >
                        <TextArea
                            rows={3}
                            value={userQuery}
                            onChange={handleQueryChange}
                            placeholder="Örn: 2247-C programı kapsamında 6 aylık bir araştırma planı oluşturmak istiyorum..."
                        />
                    </Form.Item>

                    <Form.Item>
                        <Button
                            type="primary"
                            icon={<SendOutlined />}
                            onClick={generatePlan}
                            loading={loading}
                            disabled={!selectedFon}
                            block
                        >
                            Plan Oluştur
                        </Button>
                    </Form.Item>
                </Form>

                {error && (
                    <Alert
                        message="Hata"
                        description={error}
                        type="error"
                        showIcon
                        style={{ marginBottom: 20 }}
                    />
                )}

                {loading && (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                        <Spin size="large" tip="Agent AI plan oluşturuyor..." />
                        <Paragraph style={{ marginTop: 16 }}>
                            LSTM modeli değerlendirmesini yapıyor ve en uygun planı hazırlıyor...
                        </Paragraph>
                    </div>
                )}

                {plan && (
                    <div className="plan-container">
                        <Divider>
                            <Tag color="blue" style={{ fontSize: 16, padding: '4px 8px' }}>
                                Oluşturulan Plan
                            </Tag>
                        </Divider>

                        <Card
                            bordered={true}
                            style={{ marginBottom: 16 }}
                        >
                            <div style={{ whiteSpace: 'pre-line' }}>
                                {plan}
                            </div>
                        </Card>

                        {renderResearchSteps()}

                        <Divider />

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                            <div>
                                <Button
                                    type="primary"
                                    icon={<DownloadOutlined />}
                                    onClick={downloadPDF}
                                    disabled={!planId}
                                >
                                    PDF İndir
                                </Button>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                                <Text style={{ marginBottom: 8 }}>Plan kalitesini değerlendirin:</Text>
                                <Rate
                                    allowHalf
                                    value={feedbackScore}
                                    onChange={setFeedbackScore}
                                    disabled={feedbackSent}
                                />
                                {!feedbackSent ? (
                                    <Button
                                        type="link"
                                        onClick={sendFeedback}
                                        disabled={!feedbackScore}
                                        style={{ marginTop: 8 }}
                                    >
                                        Geri bildirim gönder
                                    </Button>
                                ) : (
                                    <Text type="success" style={{ marginTop: 8 }}>
                                        <CheckCircleOutlined /> Geri bildirim gönderildi
                                    </Text>
                                )}
                            </div>
                        </div>

                        {renderMetadata()}
                    </div>
                )}
            </Card>

            <Modal
                title={
                    <div style={{ display: 'flex', alignItems: 'center' }}>
                        <RobotOutlined style={{ fontSize: 20, marginRight: 8, color: '#1890ff' }} />
                        <span>LSTM Agent AI Nasıl Çalışır?</span>
                    </div>
                }
                open={infoModalVisible}
                onCancel={handleModalClose}
                footer={[
                    <Button key="close" onClick={handleModalClose}>
                        Anladım
                    </Button>
                ]}
                width={700}
            >
                <Tabs defaultActiveKey="1">
                    <TabPane tab="Genel Bilgi" key="1">
                        <Paragraph>
                            <strong>Agent AI</strong>, TÜBİTAK fon programları için akıllı araştırma planları oluşturan,
                            LSTM (Long Short-Term Memory) derin öğrenme modeli kullanarak geliştirilmiş yapay zeka ajanıdır.
                        </Paragraph>

                        <Title level={4}>Özellikler:</Title>
                        <ul>
                            <li>Fon programına özel planlar oluşturma</li>
                            <li>Araştırma süresi ve içeriğine uygun zaman çizelgeleri belirleme</li>
                            <li>Kullanıcı geri bildirimleriyle sürekli gelişen yapay zeka</li>
                            <li>PDF formatında profesyonel çıktılar üretme</li>
                        </ul>
                    </TabPane>

                    <TabPane tab="Nasıl Kullanılır" key="2">
                        <ol>
                            <li>Soldaki menüden TÜBİTAK fon programını seçin</li>
                            <li>İsterseniz sorgu kutusuna daha spesifik bir istek yazın</li>
                            <li>"Plan Oluştur" düğmesine tıklayın</li>
                            <li>Oluşturulan planı inceleyin ve PDF olarak indirin</li>
                            <li>Planın kalitesini değerlendirin ve geri bildirim yapın</li>
                        </ol>

                        <Paragraph>
                            <InfoCircleOutlined style={{ color: '#1890ff' }} /> <strong>Not:</strong> Geri bildirimleriniz
                            Agent AI'ın öğrenmesini ve daha iyi planlar üretmesini sağlar.
                        </Paragraph>
                    </TabPane>

                    <TabPane tab="Teknik Bilgiler" key="3">
                        <Paragraph>
                            LSTM Agent AI, sürekli gelişen derin öğrenme modeli kullanarak, fon türlerine ve araştırma
                            sürelerine göre özelleştirilmiş planlar oluşturur.
                        </Paragraph>

                        <Title level={4}>Çalışma Prensibi:</Title>
                        <ol>
                            <li>Kullanıcı sorgusunu analiz eder</li>
                            <li>İlgili fon bilgilerini ve süreyi tespit eder</li>
                            <li>Derin öğrenme modeliyle en uygun plan şablonunu seçer</li>
                            <li>Dinamik içerik üreterek özelleştirilmiş plan oluşturur</li>
                            <li>Kullanıcı geri bildirimleriyle kendini geliştirir</li>
                        </ol>

                        <Paragraph>
                            <strong>Teknik Altyapı:</strong> LSTM (Long Short-Term Memory) derin öğrenme mimarisi,
                            TensorFlow, Django ve React
                        </Paragraph>
                    </TabPane>
                </Tabs>
            </Modal>
        </div>
    );
};

export default LSTMModel;