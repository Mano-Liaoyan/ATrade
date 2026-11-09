import { describe, expect, it } from 'vite-plus/test';
import { MAX_IMAGE_BYTES, MAX_IMAGE_COUNT, readMessageImages } from './message_images';

function imageFile(name: string, type = 'image/png', size = 2): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe('the images of a new message', () => {
  it('reads an image as base64 and as a data URL', async () => {
    const result = await readMessageImages([imageFile('a.png')], MAX_IMAGE_COUNT);

    expect(result).toEqual({
      images: [{ mimeType: 'image/png', base64: 'AAA=', url: 'data:image/png;base64,AAA=' }],
      problem: null,
    });
  });

  it('adds the files that fit and names the first file that does not', async () => {
    const result = await readMessageImages([imageFile('a.png'), imageFile('b.svg', 'image/svg+xml')], MAX_IMAGE_COUNT);

    expect(result.images).toHaveLength(1);
    expect(result.problem).toBe('b.svg was not added: use a PNG, JPEG, WebP, or GIF image.');
  });

  it('refuses a file over the size limit and a file over the count limit', async () => {
    const large = await readMessageImages([imageFile('a.png', 'image/png', MAX_IMAGE_BYTES + 1)], MAX_IMAGE_COUNT);
    const full = await readMessageImages([imageFile('a.png')], 0);

    expect(large).toEqual({ images: [], problem: 'a.png was not added: an image can have at most 3 MB.' });
    expect(full).toEqual({ images: [], problem: 'a.png was not added: a message can have at most 4 images.' });
  });
});
