import { motion } from 'framer-motion';

export type CoreState = 'IDLE' | 'THINKING' | 'EXECUTING' | 'WAITING' | 'SUCCESS' | 'FAILED';

export function JarvisCore({ state }: { state: CoreState }) {
  // Map states to visual properties
  let glowClass = 'orb-glow-idle';
  let pulseDuration = 4;
  let rotateDuration = 20;

  if (state === 'THINKING' || state === 'EXECUTING') {
    glowClass = 'orb-glow';
    pulseDuration = 1.5;
    rotateDuration = 8;
  } else if (state === 'WAITING') {
    glowClass = 'orb-glow-amber';
    pulseDuration = 2;
  } else if (state === 'SUCCESS') {
    glowClass = 'orb-glow-green';
  } else if (state === 'FAILED') {
    glowClass = 'orb-glow-red';
    pulseDuration = 0.5;
  }

  return (
    <div className="relative flex items-center justify-center w-64 h-64 mx-auto my-8">
      {/* Outer rotating ring */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: rotateDuration, ease: "linear", repeat: Infinity }}
        className="absolute inset-0 rounded-full border border-jarvis-cyan/20 border-t-jarvis-cyan/80"
        style={{ borderStyle: 'dashed' }}
      />

      {/* Inner counter-rotating ring */}
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: rotateDuration * 0.7, ease: "linear", repeat: Infinity }}
        className="absolute inset-4 rounded-full border border-jarvis-blue/30 border-b-jarvis-blue/90"
        style={{ borderStyle: 'dotted' }}
      />

      {/* Central Core */}
      <motion.div
        animate={{ scale: [0.95, 1.05, 0.95] }}
        transition={{ duration: pulseDuration, ease: "easeInOut", repeat: Infinity }}
        className={`w-24 h-24 rounded-full bg-jarvis-dark border-2 border-white/20 ${glowClass} flex items-center justify-center z-10 relative overflow-hidden`}
      >
          <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/10 to-transparent"></div>
          {/* Scanning line for active states */}
          {(state === 'THINKING' || state === 'EXECUTING') && (
              <motion.div
                 animate={{ y: ['-100%', '100%'] }}
                 transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                 className="absolute left-0 right-0 h-1 bg-white/50 shadow-[0_0_8px_#fff]"
              />
          )}
      </motion.div>
    </div>
  );
}
