// The images of a new message of the AI assistant (docs/architecture/assistant.md 25.10). The limits are the limits of
// PromptMessage in web. 4 images of 3 MB stay under the 16 MiB WebSocket limit of uvicorn.
export const MAX_IMAGE_COUNT = 4;
export const MAX_IMAGE_BYTES = 3_000_000;
const IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif'];
export const IMAGE_INPUT_ACCEPT = IMAGE_TYPES.join(',');

export interface MessageImage {
  mimeType: string;
  /** The file in base64, without the `data:` prefix. */
  base64: string;
  /** The `data:` URL, for the thumbnail. */
  url: string;
}

export interface ReadImages {
  images: MessageImage[];
  /** The reason of the first file that was not added. Null when all files were added. */
  problem: string | null;
}

function findProblem(file: File, index: number, room: number): string | null {
  if (!IMAGE_TYPES.includes(file.type)) {
    return `${file.name} was not added: use a PNG, JPEG, WebP, or GIF image.`;
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return `${file.name} was not added: an image can have at most 3 MB.`;
  }
  return index >= room ? `${file.name} was not added: a message can have at most ${String(MAX_IMAGE_COUNT)} images.` : null;
}

async function readImage(file: File): Promise<MessageImage> {
  let binary = '';
  for (const byte of new Uint8Array(await file.arrayBuffer())) {
    binary += String.fromCharCode(byte);
  }
  const base64 = btoa(binary);
  return { mimeType: file.type, base64, url: `data:${file.type};base64,${base64}` };
}

/** Reads the files that fit. `room` is the number of images that the message can still take. */
export async function readMessageImages(files: readonly File[], room: number): Promise<ReadImages> {
  const accepted: File[] = [];
  let problem: string | null = null;
  for (const file of files) {
    const fileProblem = findProblem(file, accepted.length, room);
    if (fileProblem === null) {
      accepted.push(file);
    } else {
      problem ??= fileProblem;
    }
  }
  try {
    return { images: await Promise.all(accepted.map(readImage)), problem };
  } catch (error) {
    return { images: [], problem: error instanceof Error ? error.message : String(error) };
  }
}
