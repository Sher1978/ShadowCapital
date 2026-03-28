import React from 'react';
import { motion } from 'framer-motion';

export default function ScanningOverlay({ name }) {
  const steps = [
    "Подключение инстанции Shadow AI...",
    "Синхронизация с сектором Engine...",
    "Считывание паттернов саботажа...",
    "Расчет Friction Index...",
    "Дешифровка Теневого Капитала...",
    "Финальный вердикт..."
  ];

  return (
    <div className="glass-card text-center overflow-hidden">
      <div className="scanning-line" />
      
      <motion.div 
        animate={{ scale: [1, 1.05, 1] }} 
        transition={{ repeat: Infinity, duration: 2 }}
        className="mb-8 p-6 border-gold rounded-full border-2 w-24 h-24 mx-auto flex items-center justify-center"
      >
        <div className="bg-gold w-12 h-12 rounded-full blur-xl animate-pulse" />
      </motion.div>

      <h2 className="mb-2">Сканирование: {name}</h2>
      <div className="gold-text text-xs mb-8">System Status: Active</div>

      <div className="flex flex-col gap-2">
        {steps.map((text, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 1.2 }}
            className="text-dim font-mono text-sm"
          >
            {'>'} {text}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
