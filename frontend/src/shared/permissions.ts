import { createContext, ReactNode, useContext } from "react";


export interface PermissionContextType {
    permissions: string[];
    isLoading: boolean;
    refreshPermissions: () => Promise<void>;
  }

export interface PermissionProviderProps {
    children: React.ReactNode;
}

export const PermissionContext = createContext<PermissionContextType | undefined>(
    undefined
);

export const usePermissions = (): string[] => {
    const context = useContext(PermissionContext);
    if (!context) {
      throw new Error("usePermissions must be used within a PermissionProvider");
    }
    return context.permissions;
  };
  
  export const useIsLoadingPermissions = (): boolean => {
    const context = useContext(PermissionContext);
    if (!context) {
      throw new Error(
        "useIsLoadingPermissions must be used within a PermissionProvider"
      );
    }
    return context.isLoading;
  };
  
  export const useRefreshPermissions = (): (() => Promise<void>) => {
    const context = useContext(PermissionContext);
    if (!context) {
      throw new Error(
        "useRefreshPermissions must be used within a PermissionProvider"
      );
    }
    return context.refreshPermissions;
  };
  