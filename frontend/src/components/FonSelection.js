// src/components/FonSelection.js
import React from 'react';
import './FonSelection.css';

const fonlar = [
    "2209-A Üniversite Öğrencileri Araştırma Projeleri",
    "2209-B Sanayiye Yönelik Lisans Araştırma Projeleri",
    "1001 Bilimsel ve Teknolojik Araştırma Projeleri",
    "1501 Sanayi AR-GE",
    "1507 KOBİ Ar-Ge Başlangıç",
];

function FonSelection({ onSelectFon }) {
    return (
        <div className="fon-selection-container">
            <h2>Hangi TÜBİTAK fonuna başvuru yapmak istiyorsunuz?</h2>
            <ul className="fon-list">
                {fonlar.map((fon, index) => (
                    <li key={index} onClick={() => onSelectFon(fon)}>
                        {fon}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default FonSelection;
