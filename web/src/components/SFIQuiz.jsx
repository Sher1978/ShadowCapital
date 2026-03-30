import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ShieldCheck, TrendingUp, Layout as LayoutIcon, ChevronLeft } from 'lucide-react';

const QUESTIONS = [
  // ZONE C: VITALITY (Fuel)
  { id: 'q1', zone: 'C', text: 'Уровень фоновой усталости, которую вы привыкли игнорировать?', min: 'Свежесть', max: 'Выгорание' },
  { id: 'q2', zone: 'C', text: 'Частота имитации бурной деятельности вместо реальных прорывов?', min: 'Никогда', max: 'Постоянно' },
  { id: 'q3', zone: 'C', text: 'Сила сопротивления перед началом действительно важной задачи?', min: 'Поток', max: 'Паралич' },
  
  // ZONE B: SOVEREIGN (Transmission)
  { id: 'q4', zone: 'B', text: 'Насколько часто вы "сглаживаете углы" в ущерб своим интересам?', min: 'Никогда', max: 'Всегда' },
  { id: 'q5', zone: 'B', text: 'Уровень дискомфорта при необходимости "ударить по столу"?', min: 'Легко', max: 'Невозможно' },
  { id: 'q6', zone: 'B', text: 'Влияние токсичного окружения на скорость ваших решений?', min: 'Ноль', max: 'Критическое' },
  
  // ZONE A: EXPANSION (Engine)
  { id: 'q7', zone: 'A', text: 'Масштаб финансовой цели, которую вы откладываете больше года?', min: 'Уже в пути', max: 'Заморожена' },
  { id: 'q8', zone: 'A', text: 'Страх потери текущей стабильности при рывке в x10?', min: 'Драйв', max: 'Ужас' },
  { id: 'q9', zone: 'A', text: 'Уровень сложности делегирования ключевых процессов?', min: 'Автопилот', max: 'Ручное упр.' },
  
  // ZONE D: ARCHITECT (Body)
  { id: 'q10', zone: 'D', text: 'Уровень неловкости при публичной трансляции своего успеха?', min: 'Естественно', max: 'Стыдно' },
  { id: 'q11', zone: 'D', text: 'Тяга оставаться "в тени" вместо того, чтобы стать лицом системы?', min: 'Я лидер', max: 'Невидимка' },
  { id: 'q12', zone: 'D', text: 'Несоответствие вашего реального IQ вашему медийному весу?', min: 'Баланс', max: 'Пропасть' }
];

const ZONES = {
  'C': { label: 'Vitality Sector', icon: Activity },
  'B': { label: 'Sovereign Sector', icon: ShieldCheck },
  'A': { label: 'Expansion Sector', icon: TrendingUp },
  'D': { label: 'Architect Sector', icon: LayoutIcon }
};

export default function SFIQuiz({ onComplete }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [userData, setUserData] = useState({ name: '', contact: '' });
  const [isIntro, setIsIntro] = useState(true);

  const currentQuestion = QUESTIONS[step];
  const progress = ((step) / QUESTIONS.length) * 100;

  const handleAnswer = (value) => {
    const newAnswers = { ...answers, [currentQuestion.id]: value };
    setAnswers(newAnswers);
    
    if (step < QUESTIONS.length - 1) {
      setTimeout(() => setStep(step + 1), 200);
    } else {
      onComplete(userData, newAnswers);
    }
  };

  if (isIntro) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="ios-card"
      >
        <div className="sector-header">
          <span className="sector-tag">Classification: SFI Diagnostic</span>
          <h1 style={{ marginBottom: '0.5rem', fontSize: '2.4rem' }}>SHADOW SCAN <span className="gold-text" style={{ fontSize: '1rem', verticalAlign: 'middle' }}>v2.6</span></h1>
          <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Оцифруй свою систему и выяви скрытый «Налог на Трение».</p>
        </div>
        
        <div style={{ marginTop: '2.5rem' }}>
          <div className="ios-input-group">
            <label className="ios-label">Имя Оператора</label>
            <input 
              className="ios-input" 
              placeholder="e.g. Александр" 
              style={{ 
                border: !userData.name ? '1px solid rgba(255, 59, 48, 0.4)' : '1px solid rgba(212, 175, 55, 0.2)' 
              }}
              value={userData.name}
              onChange={(e) => setUserData({ ...userData, name: e.target.value })}
            />
          </div>
          <div className="ios-input-group" style={{ marginBottom: '3rem' }}>
            <label className="ios-label">Telegram или Email</label>
            <input 
              className="ios-input" 
              placeholder="@username" 
              style={{ 
                border: !userData.contact ? '1px solid rgba(255, 59, 48, 0.4)' : '1px solid rgba(212, 175, 55, 0.2)' 
              }}
              value={userData.contact}
              onChange={(e) => setUserData({ ...userData, contact: e.target.value })}
            />
          </div>
          
          <button 
            className="ios-btn-gold"
            disabled={!userData.name || !userData.contact}
            onClick={() => {
              if (userData.name && userData.contact) {
                setIsIntro(false);
              }
            }}
            style={{ 
              opacity: (!userData.name || !userData.contact) ? 0.3 : 1,
              cursor: (!userData.name || !userData.contact) ? 'not-allowed' : 'pointer'
            }}
          >
            Запустить сканирование
            <Activity size={18} />
          </button>
        </div>
      </motion.div>
    );
  }

  const ZoneIcon = ZONES[currentQuestion.zone].icon;

  return (
    <motion.div 
      key={step}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="ios-card"
    >
      <div className="sector-header">
        <span className="sector-tag">
          <ZoneIcon size={12} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
          {ZONES[currentQuestion.zone].label}
        </span>
        <h2 className="question-text">{currentQuestion.text}</h2>
      </div>

      <div className="answer-grid-premium">
        {[...Array(11)].map((_, i) => (
          <div
            key={i}
            className={`answer-pill ${answers[currentQuestion.id] === i ? 'active' : ''}`}
            onClick={() => handleAnswer(i)}
          >
            {i}
          </div>
        ))}
      </div>

      <div className="grid-labels">
        <span>{currentQuestion.min}</span>
        <span>{currentQuestion.max}</span>
      </div>

      <div className="progress-container">
        <motion.div 
          className="progress-bar-fill"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
        />
      </div>

      <div className="flex justify-between items-center mt-8">
        <button 
          className="btn-secondary"
          style={{ padding: '0.6rem 1rem', fontSize: '0.7rem', opacity: step === 0 ? 0 : 1 }}
          disabled={step === 0}
          onClick={() => setStep(step - 1)}
        >
          <ChevronLeft size={14} style={{ marginRight: '4px' }} /> Назад
        </button>
        
        <div className="gold-text" style={{ fontSize: '0.7rem' }}>
          {step + 1} / {QUESTIONS.length}
        </div>
      </div>
    </motion.div>
  );
}
