import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import confetti from 'canvas-confetti';
import { Send, Download, ExternalLink } from 'lucide-react';

export default function ResultsDisplay({ result, onRestart }) {
  const { sfi_score, archetype, insight, uuid } = result;
  
  // Interpretation based on SFI
  const sfiLabel = sfi_score < 30 ? "Shadow Master" : sfi_score < 70 ? "Shadow Integrated" : "Shadow Seeker";
  const sfiColor = sfi_score < 30 ? "#03dac6" : sfi_score < 70 ? "#bb86fc" : "#ff4b2b";

  useEffect(() => {
    if (sfi_score < 50) {
      confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#d4af37', '#ffffff'] });
    }
  }, [sfi_score]);

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card max-w-[800px]"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* Left Column: SFI Score */}
        <div className="flex flex-col items-center">
          <div className="gold-text mb-4">Your Shadow Profile</div>
          <motion.div 
            initial={{ rotate: -90, opacity: 0 }}
            animate={{ rotate: 0, opacity: 1 }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            className="relative w-48 h-48 flex items-center justify-center border-4 rounded-full"
            style={{ borderColor: sfiColor, boxShadow: `0 0 30px ${sfiColor}44` }}
          >
            <div className="text-5xl font-bold">{sfi_score}%</div>
            <div className="absolute -bottom-4 bg-black border px-3 py-1 text-[10px] gold-text rounded-full" style={{ borderColor: sfiColor }}>
              SFI INDEX
            </div>
          </motion.div>
          
          <h2 className="mt-12 mb-0" style={{ color: sfiColor }}>{sfiLabel}</h2>
          <div className="text-dim text-sm font-mono mt-2 uppercase tracking-widest">{archetype} Archetype</div>
          
          <div className="bg-white/5 border border-white/10 p-4 rounded-xl mt-8 w-full">
            <div className="text-xs gold-text mb-2">Technical Insight:</div>
            <p className="text-sm italic text-dim font-mono leading-relaxed">
              "{insight}"
            </p>
          </div>
        </div>

        {/* Right Column: Next Steps */}
        <div className="flex flex-col justify-center">
          <h3>Твоя стратегия адаптации</h3>
          <p className="text-dim text-sm mb-8">
            Твой результат в секции <span className="text-white font-bold">{archetype}</span> указывает на то, что Тень забирает до 60% твоей эффективности. 
            Это "Налог на Порядочность", который можно конвертировать в Капитал.
          </p>

          <div className="flex flex-col gap-4">
            <a 
              href={`https://t.me/Shadowass1st_bot?start=${uuid}`} 
              target="_blank" 
              className="btn-primary flex items-center justify-between group"
            >
              <span>Получить PDF-анализ в TG</span>
              <Send size={18} className="transition-transform group-hover:translate-x-1" />
            </a>
            
            <button 
              className="btn-secondary flex items-center justify-between"
              onClick={() => window.open('https://shershadowcapital.com/audit')}
            >
              <span>Записаться на Shadow Audit</span>
              <ExternalLink size={16} />
            </button>
            
            <button className="text-xs text-dim hover:text-white mt-4 font-mono underline" onClick={onRestart}>
              Перезапустить систему сканирования
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
