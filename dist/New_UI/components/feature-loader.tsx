import { useState, useEffect } from 'react';

interface FeatureLoaderProps {
    feature: string;
    children: React.ReactNode;
    fallback?: React.ReactNode;
}

export function FeatureLoader({ feature, children, fallback }: FeatureLoaderProps) {
    const [isLoaded, setIsLoaded] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadFeature = async () => {
            try {
                setIsLoading(true);
                
                // Check if feature is already available
                const response = await fetch(`/api/check-feature?feature=${feature}`);
                const { available } = await response.json();
                
                if (available) {
                    setIsLoaded(true);
                    return;
                }
                
                // Install feature
                const installResponse = await fetch('/api/install-feature', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ feature })
                });
                
                if (installResponse.ok) {
                    setIsLoaded(true);
                } else {
                    setError('Failed to install feature');
                }
            } catch (err) {
                setError('Failed to load feature');
            } finally {
                setIsLoading(false);
            }
        };
        
        loadFeature();
    }, [feature]);

    if (error) {
        return <div>Error: {error}</div>;
    }
    
    if (isLoading) {
        return <div>Installing {feature}...</div>;
    }
    
    if (!isLoaded) {
        return fallback || <div>Feature not available</div>;
    }
    
    return <>{children}</>;
}