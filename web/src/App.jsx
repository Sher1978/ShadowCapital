import React, { useState } from 'react';
import { initializeApp } from 'firebase/app';
import { getFunctions, httpsCallable } from 'firebase/functions';
import SFIQuiz from './components/SFIQuiz';
import ScanningOverlay from './components/ScanningOverlay';
import ResultsDisplay from './components/ResultsDisplay';
import { motion, AnimatePresence } from 'framer-motion';

// Replace with actual Firebase config from user
const firebaseConfig = {
  apiKey: "AIzaSyCO50Ya5Er5NbRDUASk0CNvoGKc5W9gqKw",
  authDomain: "shershadow.firebaseapp.com",
  projectId: "shershadow",
  storageBucket: "shershadow.firebasestorage.app",
  messagingSenderId: "1097154359322",
  appId: "1:1097154359322:web:14549af3c785da87ffa1a3",
  measurementId: "G-0VJF4VV3H5"
};

const app = initializeApp(firebaseConfig);
const functions = getFunctions(app);

export default function App() {
  const [view, setView] = useState('quiz'); // quiz, scanning, result
  const [result, setResult] = useState(null);
  const [userName, setUserName] = useState('');

  const handleQuizComplete = async (userData, answers) => {
    setUserName(userData.name);
    setView('scanning');
    
    try {
      // Simulate/Wait for scanning effect
      const minScanTime = new Promise(resolve => setTimeout(resolve, 6000));
      
      const calculateSfi = httpsCallable(functions, 'calculate_sfi');
      const response = await calculateSfi({
        name: userData.name,
        contact: userData.contact,
        answers: answers
      });

      await minScanTime;
      setResult(response.data);
      setView('result');
    } catch (error) {
      console.error("Error calculating SFI:", error);
      alert("Ошибка подключения к системе. Проверьте соединение.");
      setView('quiz');
    }
  };

  return (
    <div className="app-container">
      <div className="blueprint-bg" />
      
      <AnimatePresence mode="wait">
        <motion.div
          key={view}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 1.1 }}
          transition={{ duration: 0.5 }}
          className="w-full flex justify-center"
        >
          {view === 'quiz' && (
            <SFIQuiz onComplete={handleQuizComplete} />
          )}
          
          {view === 'scanning' && (
            <ScanningOverlay name={userName} />
          )}
          
          {view === 'result' && result && (
            <ResultsDisplay 
              result={result} 
              onRestart={() => setView('quiz')} 
            />
          )}
        </motion.div>
      </AnimatePresence>

      <footer className="fixed bottom-8 text-dim text-[10px] font-mono tracking-widest opacity-30 select-none">
        PROPRIETARY SYSTEM // SHERLOCK SHADOW CAPITAL // ID: 0xFF921
      </footer>
    </div>
  );
}
