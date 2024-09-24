package com.renderer;

import java.nio.file.Path;

import com.atlassian.jira.issue.Issue;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.attachments.RendererAttachment;
import com.atlassian.renderer.attachments.RendererAttachmentManager;
import com.atlassian.renderer.embedded.EmbeddedImage;
import com.atlassian.renderer.embedded.EmbeddedResource;
import com.google.gson.JsonObject;

public class FakeAttachmentManager implements RendererAttachmentManager {
   private final Path attachFolder;
   private JsonObject attachmentMap = null;

   public FakeAttachmentManager(Path attachFolder) {
      this.attachFolder = attachFolder;
   }

   public void setAttachmentMap(JsonObject attachMap) {
      this.attachmentMap = attachMap;
   }

   public RendererAttachment getAttachment(RenderContext context, EmbeddedResource resource) {
      var issue = (Issue) context.getParam("jira.issue");
      if (issue == null)
         return null;
      var issue_attachments = attachmentMap.get(issue.getId().toString());
      if (issue_attachments == null)
         return null;
      var attachment_id = issue_attachments.getAsJsonObject().get(resource.getFilename());
      if (attachment_id == null)
         return null;
      return new RendererAttachment(attachment_id.getAsLong(), resource.getFilename(), null, null, null, null, null,
            null, null);
   }

   public RendererAttachment getThumbnail(RendererAttachment attachment, RenderContext context,
         EmbeddedImage resource) {
      return attachment;
   }

   public boolean systemSupportsThumbnailing() {
      return true;
   }
}
