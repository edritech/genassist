import React, {
  useState,
  useEffect,
} from "react";
import { apiRequest } from "@/config/api";
import { isServerDown } from "@/config/serverStatus";
import { isAuthenticated } from "@/services/auth";
import { PermissionProviderProps } from "@/shared/permissions";
import { PermissionContext } from "@/shared/permissions";


export const PermissionProvider: React.FC<PermissionProviderProps> = ({
  children,
}) => {
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchPermissions = async () => {
    if (!isAuthenticated()) {
      setIsLoading(false);
      return;
    }

    // If server is down avoid requests
    if (isServerDown() || (typeof navigator !== 'undefined' && !navigator.onLine)) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiRequest("GET", "/auth/me");
      const userPermissions: string[] =
        (response as { permissions: string[] })?.permissions || [];
      setPermissions(userPermissions);
    } catch (error) {
      // Quiet known down-state errors
      if ((error as Error)?.message !== 'SERVER_DOWN') {
        // ignore
      }
    }
    setIsLoading(false);
  };

  useEffect(() => {
    fetchPermissions();
  }, []);

  return (
    <PermissionContext.Provider
      value={{
        permissions,
        isLoading,
        refreshPermissions: fetchPermissions,
      }}
    >
      {children}
    </PermissionContext.Provider>
  );
};
