export {};

declare global {
  interface Window {
    electronAPI?: {
      backendBaseUrl: string;
      platform: string;
      versions: NodeJS.ProcessVersions;
      selectVideoFile?: () => Promise<string | null>;
      pathToFileUrl?: (filePath: string) => string;
    };
  }
}
