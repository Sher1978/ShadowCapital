import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, ShieldCheck, Activity, TrendingUp, Layout } from 'lucide-react';

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
  'C': { label: 'Vitality', icon: Activity, color: '#ff4b2b' },
  'B': { label: 'Sovereign', icon: ShieldCheck, color: '#bb86fc' },
  'A': { label: 'Expansion', icon: TrendingUp, color: '#03dac6' },
  'D': { label: 'Architect', icon: Layout, color: '#d4af37' }
};

export default function SFIQuiz({ onComplete }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState({});
  const [userData, setUserData] = useState({ name: '', contact: '' });
  const [isIntro, setIsIntro] = useState(true);

  const currentQuestion = QUESTIONS[step];
  const progress = ((step + 1) / QUESTIONS.length) * 100;

  const handleAnswer = (value) => {
    const newAnswers = { ...answers, [currentQuestion.id]: value };
    setAnswers(newAnswers);
    
    if (step < QUESTIONS.length - 1) {
      setStep(step + 1);
    } else {
      onComplete(userData, newAnswers);
    }
  };

  if (isIntro) {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card"
      >
        <div className="gold-text mb-2">Shadow Scan v2.0</div>
        <h1>Начни дешифровку своей системы</h1>
        <p className="text-dim mb-8">
          Этот тест оцифрует твой «Налог на Трение» — скрытую цену, которую ты платишь за внутренний саботаж.
        </p>
        
        <input 
          className="input-field" 
          placeholder="Твое Имя" 
          value={userData.name}
          onChange={(e) => setUserData({ ...userData, name: e.target.value })}
        />
        <input 
          className="input-field" 
          placeholder="Telegram или Email" 
          value={userData.contact}
          onChange={(e) => setUserData({ ...userData, contact: e.target.value })}
        />
        
        <button 
          className="btn-primary w-full"
          disabled={!userData.name || !userData.contact}
          onClick={() => setIsIntro(false)}
        >
          Запустить сканирование
        </button>
      </motion.div>
    );
  }

  const ZoneIcon = ZONES[currentQuestion.zone].icon;

  return (
    <div className="glass-card">
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-2">
          <ZoneIcon size={18} color={ZONES[currentQuestion.zone].color} />
          <span className="gold-text">{ZONES[currentQuestion.zone].label} Sector</span>
        </div>
        <div className="text-xs font-mono opacity-50">{step + 1} / {QUESTIONS.length}</div>
      </div>

      <div className="w-full bg-metal h-1 mb-10 overflow-hidden rounded-full">
        <motion.div 
          className="bg-gold h-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
        />
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
        >
          <h2 className="mb-12 min-h-[4rem]">{currentQuestion.text}</h2>
          
          <div className="flex flex-col gap-4">
            <div className="flex justify-between text-xs font-mono text-dim mb-2">
              <span>{currentQuestion.min}</span>
              <span>{currentQuestion.max}</span>
            </div>
            
            <div className="grid grid-cols-11 gap-1">
              {[...Array(11)].map((_, i) => (
                <button
                  key={i}
                  className={`h-12 border border-metal rounded transition-all active:scale-95 flex items-center justify-center font-bold text-xs
                    ${answers[currentQuestion.id] === i 
                      ? 'bg-gold border-gold text-black shadow-[0_0_15px_rgba(212,175,55,0.4)]' 
                      : 'hover:bg-white/5 text-dim'}`}
                  onClick={() => handleAnswer(i)}
                >
                  {i}
                </button>
              ))}
            </div>
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="mt-12 flex justify-between">
        <button 
          className="btn-secondary flex items-center gap-2"
          disabled={step === 0}
          onClick={() => setStep(step - 1)}
        >
          <ChevronLeft size={16} /> Назад
        </button>
      </div>
    </div>
  );
}
