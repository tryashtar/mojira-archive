"use strict";
async function decompressString(compressed, compressedLength) {
    const bytes = new Uint8Array(compressedLength);
    let byteIndex = 0;
    for (let i = 0; byteIndex + 1 < compressedLength; i++) {
        const value = compressed.charCodeAt(i);
        bytes[byteIndex++] = value & 0xff;
        bytes[byteIndex++] = value >>> 8;
    }
    if (byteIndex < compressedLength) {
        bytes[byteIndex] = compressed.charCodeAt(compressed.length - 1) & 0xff;
    }
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
    const decompressed = await new Response(stream).arrayBuffer();
    return new TextDecoder().decode(decompressed);
}
