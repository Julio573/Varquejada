export {};

declare global {
  interface Window {
    electronAPI?: {
      backendBaseUrl: string;
      platform: string;
      versions: NodeJS.ProcessVersions;
      openAnalysisWindow?: () => Promise<boolean>;
      closeAnalysisWindow?: () => Promise<boolean>;
      selectVideoFile?: () => Promise<string | null>;
      pathToFileUrl?: (filePath: string) => string;
    };
  }
}
