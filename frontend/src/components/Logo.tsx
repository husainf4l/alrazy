import Link from 'next/link';

interface LogoProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showText?: boolean;
  href?: string | null;
  className?: string;
  textClassName?: string;
  iconClassName?: string;
  theme?: 'light' | 'dark';
}

const Logo = ({ 
  size = 'md', 
  showText = true, 
  href = '/', 
  className = '',
  textClassName = '',
  iconClassName = '',
  theme = 'light'
}: LogoProps) => {
  // Size configurations
  const sizeConfig = {
    sm: {
      container: 'w-6 h-6',
      inner: 'w-3 h-3',
      text: 'text-base',
      spacing: 'ml-2'
    },
    md: {
      container: 'w-8 h-8',
      inner: 'w-4 h-4',
      text: 'text-xl',
      spacing: 'ml-3'
    },
    lg: {
      container: 'w-12 h-12',
      inner: 'w-6 h-6',
      text: 'text-2xl',
      spacing: 'ml-4'
    },
    xl: {
      container: 'w-16 h-16 md:w-20 md:h-20',
      inner: 'w-8 h-8 md:w-10 md:h-10',
      text: 'text-3xl md:text-4xl',
      spacing: 'ml-4 md:ml-5'
    }
  };

  const config = sizeConfig[size];

  const LogoContent = () => (
    <div className={`flex items-center justify-center ${className}`}>
      <div className={`${config.container} bg-gradient-to-br from-red-500 via-orange-500 to-yellow-500 rounded-xl flex items-center justify-center shadow-lg ${iconClassName}`}>
        <div className={`${config.inner} bg-white rounded-md opacity-95`}></div>
      </div>
      {showText && (
        <span className={`${config.spacing} ${config.text} font-bold tracking-tight ${
          theme === 'dark' ? 'text-white' : 'text-gray-900'
        } ${textClassName}`}>
          RazZ Security
        </span>
      )}
    </div>
  );

  // If href is provided, wrap in Link, otherwise return as div
  if (href) {
    return (
      <Link href={href} className="inline-block">
        <LogoContent />
      </Link>
    );
  }

  return <LogoContent />;
};

export default Logo;
