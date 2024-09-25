package com.renderer;

import java.io.IOException;
import java.util.Collection;

import org.ofbiz.core.entity.GenericEntityException;

import com.atlassian.core.util.thumbnail.Thumbnail;
import com.atlassian.jira.issue.Issue;
import com.atlassian.jira.issue.attachment.Attachment;
import com.atlassian.jira.issue.thumbnail.ThumbnailManager;
import com.atlassian.jira.issue.thumbnail.ThumbnailedImage;
import com.atlassian.jira.user.ApplicationUser;
import com.atlassian.jira.util.io.InputStreamConsumer;

public class FakeThumbnailManager implements ThumbnailManager {
   public boolean isThumbnailable(Attachment attachment) throws GenericEntityException {
      return attachment.isThumbnailable();
   }

   public Thumbnail getThumbnail(Attachment attachment) {
      var mimeType = attachment.getMimetype();
      if (mimeType == "image/jpeg") {
         return new Thumbnail(0, 0, attachment.getFilename(), attachment.getId(), Thumbnail.MimeType.JPG);
      } else if (mimeType == "image/png") {
         return new Thumbnail(0, 0, attachment.getFilename(), attachment.getId(), Thumbnail.MimeType.PNG);
      } else {
         return new Thumbnail(0, 0, attachment.getFilename(), attachment.getId());
      }
   }

   public ThumbnailedImage toThumbnailedImage(Thumbnail thumbnail) {
      return new ThumbnailedImage() {
         public long getAttachmentId() {
            return thumbnail.getAttachmentId();
         }

         public String getFilename() {
            return thumbnail.getFilename();
         }

         public int getHeight() {
            return thumbnail.getHeight();
         }

         public int getWidth() {
            return thumbnail.getWidth();
         }

         public String getImageURL() {
            return "https://bugs.mojang.com/secure/thumbnail/" + getAttachmentId() + "/_thumb_" + getAttachmentId()
                  + ".png";
         }

         public String getMimeType() {
            return thumbnail.getMimeType().toString();
         }
      };
   }

   public boolean checkToolkit() {
      throw new UnsupportedOperationException();
   }

   public void deleteThumbnailForAttachment(Issue arg0, Attachment arg1) {
      throw new UnsupportedOperationException();
   }

   public void deleteThumbnailsForIssue(Issue arg0) {
      throw new UnsupportedOperationException();
   }

   public Thumbnail getThumbnail(Issue arg0, Attachment arg1) {
      throw new UnsupportedOperationException();
   }

   public Thumbnail getThumbnailDeferred(Issue arg0, Attachment arg1) {
      throw new UnsupportedOperationException();
   }

   public Collection<Thumbnail> getThumbnails(Issue arg0, ApplicationUser arg1) throws Exception {
      throw new UnsupportedOperationException();
   }

   public boolean isThumbnailable(Issue arg0, Attachment arg1) throws GenericEntityException {
      throw new UnsupportedOperationException();
   }

   public <T> T streamThumbnailContent(Attachment arg0, InputStreamConsumer<T> arg1) throws IOException {
      throw new UnsupportedOperationException();
   }
}
