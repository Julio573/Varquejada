export type CameraDeviceInfo = {
  index: number;
  deviceId: string;
  groupId: string;
  label: string;
};

async function unlockCameraLabels() {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    throw new Error("Este ambiente não oferece acesso à câmera.");
  }

  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  stream.getTracks().forEach((track) => track.stop());
}

export async function listCameraDevices() {
  await unlockCameraLabels();

  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices
    .filter((device) => device.kind === "videoinput")
    .map((device, index) => ({
      index,
      deviceId: device.deviceId,
      groupId: device.groupId,
      label: device.label?.trim() || `Câmera ${index + 1}`,
    }));
}
