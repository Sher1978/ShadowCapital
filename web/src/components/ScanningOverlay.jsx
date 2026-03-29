import React from 'react';
import { motion } from 'framer-motion';

export default function ScanningOverlay({ name }) {
  const steps = [
    "Подключение инстанции Shadow AI...",
    "Синхронизация с сектором Engine...",
    "Считывание паттернов саботажа...",
    "Расчет Friction Index...",
    "Дешифровка Теневого Капитала...",
    "Генерация персонального досье..."
  ];

  return (
    <div className="ios-card text-center overflow-hidden" style={{ minHeight: '400px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <div className="scanning-line" />
      
      <motion.div 
        animate={{ 
          scale: [1, 1.1, 1],
          opacity: [0.5, 1, 0.5]
        }} 
        transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
        className="mb-8 p-6 w-24 h-24 mx-auto flex items-center justify-center relative"
      >
        <div className="absolute inset-0 bg-gold rounded-full blur-2xl opacity-20" />
        <div className="border-gold rounded-full border-[1px] w-full h-full flex items-center justify-center relative z-10" style={{ boxShadow: '0 0 20px rgba(212, 175, 55, 0.2)' }}>
           <div className="bg-gold w-4 h-4 rounded-full shadow-[0_0_15px_#d4af37]" />
        </div>
      </motion.div>

      <h2 className="mb-2" style={{ fontSize: '1.25rem', fontWeight: '300', letterSpacing: '0.05em' }}>
        Анализ: <span className="gold-text">{name}</span>
      </h2>
      <div className="gold-text font-mono text-[10px] mb-10 tracking-[0.2em] uppercase opacity-60">
        System Status: Deep Scan Active
      </div>

      <div className="flex flex-col gap-3 max-w-[280px] mx-auto text-left">
        {steps.map((text, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.8, duration: 0.5 }}
            className="text-dim font-mono text-[11px] leading-relaxed flex items-start gap-2"
            style={{ color: i === steps.length - 1 ? 'var(--gold)' : 'rgba(255,255,255,0.4)' }}
          >
            <span className="opacity-50">[{i+1}]</span> 
            <span>{text}</span>
          </motion.div>
        ))}
      </div>
      
      <motion.div 
        className="mt-12 text-[9px] font-mono opacity-20 tracking-tighter"
        animate={{ opacity: [0.1, 0.3, 0.1] }}
        transition={{ repeat: Infinity, duration: 2 }}
      >
        NEURAL FRICTION ENGINE v.4.0.1 // ENCRYPTED_STREAM
      </motion.div>
    </div>
  );
}
