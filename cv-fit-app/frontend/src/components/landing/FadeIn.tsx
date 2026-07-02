'use client';

import { motion } from 'framer-motion';

interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'none';
  threshold?: number;
  className?: string;
  once?: boolean;
}

const variants = {
  up: {
    initial: { opacity: 0, y: 24 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 24 },
  },
  down: {
    initial: { opacity: 0, y: -24 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -24 },
  },
  left: {
    initial: { opacity: 0, x: 24 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 24 },
  },
  right: {
    initial: { opacity: 0, x: -24 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -24 },
  },
  none: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
};

export function FadeIn({
  children,
  delay = 0,
  direction = 'up',
  threshold = 0.1,
  className = '',
  once = true,
}: FadeInProps) {
  const variant = variants[direction];

  return (
    <motion.div
      initial={variant.initial}
      animate={variant.animate}
      exit={variant.exit}
      transition={{
        duration: 0.5,
        delay,
        ease: [0.25, 0.1, 0.25, 1], // ease-out cubic
      }}
      viewport={{ amount: threshold, once }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerContainer({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ amount: 0.1, once: true }}
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: 0.12,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
