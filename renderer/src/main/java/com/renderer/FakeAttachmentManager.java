package com.renderer;

import java.nio.file.Path;

import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.attachments.RendererAttachment;
import com.atlassian.renderer.attachments.RendererAttachmentManager;
import com.atlassian.renderer.embedded.EmbeddedImage;
import com.atlassian.renderer.embedded.EmbeddedResource;

public class FakeAttachmentManager implements RendererAttachmentManager {
   private final Path attachFolder;

   public FakeAttachmentManager(Path attachFolder) {
      this.attachFolder = attachFolder;
   }

   public RendererAttachment getAttachment(RenderContext context, EmbeddedResource resource) {
      throw new UnsupportedOperationException("Unimplemented method 'getAttachment'");
   }

   public RendererAttachment getThumbnail(RendererAttachment attachment, RenderContext context,
         EmbeddedImage resource) {
      throw new UnsupportedOperationException("Unimplemented method 'getThumbnail'");
   }

   public boolean systemSupportsThumbnailing() {
      throw new UnsupportedOperationException("Unimplemented method 'systemSupportsThumbnailing'");
   }
}
