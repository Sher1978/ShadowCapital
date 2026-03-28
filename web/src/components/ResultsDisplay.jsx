import React from 'react';
import { motion } from 'framer-motion';

const ResultsDisplay = ({ result, onRestart }) => {
  const { sfi_score, archetype, scores, insight, uuid } = result;
  
  // Create deep link for Telegram
  const botUsername = "Shadow_Guardian_bot"; // Update this with actual bot username if it changes
  const telegramDeepLink = `https://t.me/${botUsername}?start=${uuid}`;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="results-container glass-card"
    >
      <div className="sfi-hero">
        <span className="sfi-label">Shadow Friction Index</span>
        <div className="sfi-number">{sfi_score}%</div>
        <h2 className="gold-text" style={{ fontSize: '1.1rem', marginTop: '0', letterSpacing: '0.3em' }}>
          {archetype}
        </h2>
      </div>

      <div className="metrics-row">
        <div className="metric-card">
          <span className="metric-value">{scores?.vitality || 0}/10</span>
          <span className="metric-name">Vitality</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{scores?.sovereign || 0}/10</span>
          <span className="metric-name">Sovereign</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{scores?.expansion || 0}/10</span>
          <span className="metric-name">Expansion</span>
        </div>
        <div className="metric-card">
          <span className="metric-value">{scores?.architect || 0}/10</span>
          <span className="metric-name">Architect</span>
        </div>
      </div>

      <div className="dossier-scroll-box">
        <div style={{ whiteSpace: 'pre-line' }}>
          {insight}
        </div>
      </div>

      <div className="action-footer">
        <a 
          href={telegramDeepLink} 
          className="btn-tg-deep"
          target="_blank" 
          rel="noopener noreferrer"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: '24px', height: '24px' }}>
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.11.02-1.93 1.23-5.46 3.62-.51.35-.98.52-1.4.51-.46-.01-1.35-.26-2.01-.48-.81-.27-1.45-.42-1.39-.88.03-.24.36-.48.99-.74 3.88-1.69 6.47-2.8 7.74-3.35 3.69-1.59 4.45-1.87 4.95-1.88.11 0 .35.03.51.16.13.11.17.26.19.37.02.13.02.39 0 .58z"/>
          </svg>
          Получить полное SFI-Досье в TG
        </a>
        <button className="btn-secondary" onClick={onRestart} style={{ border: 'none', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', marginTop: '1rem', color: '#94949e', fontSize: '0.8rem' }}>
          Пройти тест заново
        </button>
      </div>
    </motion.div>
  );
};

export default ResultsDisplay;
