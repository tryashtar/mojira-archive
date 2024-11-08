package com.renderer;

import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.sql.Timestamp;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Comparator;
import java.util.Date;
import java.util.List;
import java.util.Map;

import org.ofbiz.core.entity.GenericValue;
import org.ofbiz.core.entity.model.ModelEntity;
import org.ofbiz.core.entity.model.ModelField;

import com.atlassian.jira.exception.AttachmentNotFoundException;
import com.atlassian.jira.exception.DataAccessException;
import com.atlassian.jira.exception.RemoveException;
import com.atlassian.jira.issue.AttachmentError;
import com.atlassian.jira.issue.AttachmentManager;
import com.atlassian.jira.issue.AttachmentsBulkOperationResult;
import com.atlassian.jira.issue.Issue;
import com.atlassian.jira.issue.attachment.Attachment;
import com.atlassian.jira.issue.attachment.AttachmentReadException;
import com.atlassian.jira.issue.attachment.ConvertTemporaryAttachmentParams;
import com.atlassian.jira.issue.attachment.CreateAttachmentParamsBean;
import com.atlassian.jira.issue.attachment.NoAttachmentDataException;
import com.atlassian.jira.issue.attachment.TemporaryAttachmentId;
import com.atlassian.jira.issue.history.ChangeItemBean;
import com.atlassian.jira.task.context.Context;
import com.atlassian.jira.user.ApplicationUser;
import com.atlassian.jira.util.io.InputStreamConsumer;
import com.atlassian.jira.web.action.issue.TemporaryAttachmentsMonitor;
import com.atlassian.jira.web.util.AttachmentException;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

import io.atlassian.fugue.Either;

public class FakeAttachmentManager implements AttachmentManager {
    private final Path attachmentFolder;
    private static final ModelEntity attachmentModel;

    static {
        attachmentModel = new ModelEntity();
        attachmentModel.addField(new ModelField("id", "", "", false, List.of()));
        attachmentModel.addField(new ModelField("mimetype", "", "", false, List.of()));
        attachmentModel.addField(new ModelField("filename", "", "", false, List.of()));
        attachmentModel.addField(new ModelField("author", "", "", false, List.of()));
        attachmentModel.addField(new ModelField("created", "", "", false, List.of()));
        attachmentModel.addField(new ModelField("thumbnailable", "", "", false, List.of()));
    }

    public FakeAttachmentManager(Path attachmentFolder) {
        this.attachmentFolder = attachmentFolder;
    }

    public Attachment getAttachment(Long id) throws DataAccessException, AttachmentNotFoundException {
        var path = attachmentFolder.resolve(id.toString() + ".json");
        JsonObject data;
        try {
            data = JsonParser.parseReader(new FileReader(path.toFile())).getAsJsonObject();
        } catch (IOException ex) {
            throw new AttachmentNotFoundException(id);
        }
        var value = new GenericValue(null, attachmentModel);
        value.set("id", Long.parseLong(data.get("id").getAsString()));
        value.set("mimetype", data.get("mimeType").getAsString());
        value.set("filename", data.get("filename").getAsString());
        var author = data.get("author");
        if (author != null) {
            value.set("author", author.getAsString());
        }
        value.set("created", parseTime(data.get("created").getAsString()));
        var thumbnail = data.get("thumbnail");
        if (thumbnail != null) {
            value.set("thumbnailable", 1);
        } else {
            value.set("thumbnailable", 0);
        }
        return new Attachment(null, value);
    }

    public static Timestamp parseTime(String timeStr) {
        var formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss[.SSS][XXX][X]");
        var time = OffsetDateTime.parse(timeStr, formatter);
        return Timestamp.from(time.toInstant());
    }

    public boolean attachmentsEnabled() {
        throw new UnsupportedOperationException();
    }

    public Either<AttachmentError, ChangeItemBean> convertTemporaryAttachment(ConvertTemporaryAttachmentParams arg0) {
        throw new UnsupportedOperationException();
    }

    public List<ChangeItemBean> convertTemporaryAttachments(ApplicationUser arg0, Issue arg1, List<Long> arg2,
                                                            @SuppressWarnings("deprecation") TemporaryAttachmentsMonitor arg3) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public Either<AttachmentError, Attachment> copyAttachment(Attachment arg0, ApplicationUser arg1, String arg2) {
        throw new UnsupportedOperationException();
    }

    public Map<Long, Either<AttachmentError, Attachment>> copyAttachments(Issue arg0, ApplicationUser arg1,
                                                                          String arg2) {
        throw new UnsupportedOperationException();
    }

    public Map<Long, Either<AttachmentError, Attachment>> copyAttachments(Context arg0, Issue arg1, ApplicationUser arg2,
                                                                          String arg3) {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(CreateAttachmentParamsBean arg0) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(File arg0, String arg1, String arg2, ApplicationUser arg3, Issue arg4)
            throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(File arg0, String arg1, String arg2, ApplicationUser arg3, GenericValue arg4)
            throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(File arg0, String arg1, String arg2, ApplicationUser arg3, Issue arg4,
                                           Map<String, Object> arg5, Date arg6) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(File arg0, String arg1, String arg2, ApplicationUser arg3, GenericValue arg4,
                                           Map<String, Object> arg5, Date arg6) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public Attachment createAttachment(GenericValue arg0, ApplicationUser arg1, String arg2, String arg3, Long arg4,
                                       Map<String, Object> arg5, Date arg6) {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(File arg0, String arg1, String arg2, ApplicationUser arg3, Issue arg4,
                                           Boolean arg5, Boolean arg6, Map<String, Object> arg7, Date arg8) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public ChangeItemBean createAttachment(File arg0, String arg1, String arg2, ApplicationUser arg3, GenericValue arg4,
                                           Boolean arg5, Boolean arg6, Map<String, Object> arg7, Date arg8) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public Attachment createAttachmentCopySourceFile(File arg0, String arg1, String arg2, String arg3, Issue arg4,
                                                     Map<String, Object> arg5, Date arg6) throws AttachmentException {
        throw new UnsupportedOperationException();
    }

    public TemporaryAttachmentId createTemporaryAttachment(InputStream arg0, long arg1) {
        throw new UnsupportedOperationException();
    }

    public void deleteAttachment(Attachment arg0) throws RemoveException {
        throw new UnsupportedOperationException();
    }

    public void deleteAttachmentDirectory(Issue arg0) throws RemoveException {
        throw new UnsupportedOperationException();
    }

    public void deleteTemporaryAttachment(TemporaryAttachmentId arg0) {
        throw new UnsupportedOperationException();
    }

    public void disableAttachments() {
        throw new UnsupportedOperationException();
    }

    public List<Attachment> getAttachments(Issue arg0) throws DataAccessException {
        throw new UnsupportedOperationException();
    }

    public List<Attachment> getAttachments(Issue arg0, Comparator<? super Attachment> arg1) throws DataAccessException {
        throw new UnsupportedOperationException();
    }

    public boolean isScreenshotAppletEnabled() {
        throw new UnsupportedOperationException();
    }

    public boolean isScreenshotAppletSupportedByOS() {
        throw new UnsupportedOperationException();
    }

    public void moveAttachments(Issue arg0, String arg1) {
        throw new UnsupportedOperationException();
    }

    public Attachment setThumbnailable(Attachment arg0, boolean arg1) {
        throw new UnsupportedOperationException();
    }

    public Attachment setZip(Attachment arg0, boolean arg1) {
        throw new UnsupportedOperationException();
    }

    public <T> T streamAttachmentContent(Attachment arg0, InputStreamConsumer<T> arg1) throws IOException {
        throw new UnsupportedOperationException();
    }

    public <T> T streamTemporaryAttachmentContent(TemporaryAttachmentId arg0, InputStreamConsumer<T> arg1)
            throws AttachmentReadException, NoAttachmentDataException {
        throw new UnsupportedOperationException();
    }

    public AttachmentsBulkOperationResult<ChangeItemBean> tryConvertTemporaryAttachments(ApplicationUser arg0,
                                                                                         Issue arg1, List<Long> arg2, @SuppressWarnings("deprecation") TemporaryAttachmentsMonitor arg3) {
        throw new UnsupportedOperationException();
    }

    public Either<AttachmentError, ChangeItemBean> tryCreateAttachment(CreateAttachmentParamsBean arg0) {
        throw new UnsupportedOperationException();
    }
}