package com.renderer;

import java.util.List;
import java.util.Objects;

import com.atlassian.jira.issue.fields.renderer.wiki.embedded.ConditionalEmbeddedRenderer;
import com.atlassian.jira.issue.fields.renderer.wiki.embedded.JiraPlaceholderImageRenderer;
import com.atlassian.renderer.RenderContext;
import com.atlassian.renderer.attachments.RendererAttachmentManager;
import com.atlassian.renderer.embedded.DefaultEmbeddedResourceRenderer;
import com.atlassian.renderer.embedded.EmbeddedResource;
import com.google.common.collect.ImmutableList;

public class FakeEmbeddedResourceRenderer extends DefaultEmbeddedResourceRenderer {
   private final List<ConditionalEmbeddedRenderer> conditionalRenderers;

    public FakeEmbeddedResourceRenderer(RendererAttachmentManager attachmentManager) {
        super(attachmentManager);
        this.conditionalRenderers = this.getDefaultConditionalRenderers(attachmentManager);
    }

    private ImmutableList<ConditionalEmbeddedRenderer> getDefaultConditionalRenderers(RendererAttachmentManager attachmentManager) {
        return ImmutableList.of(new JiraPlaceholderImageRenderer(attachmentManager));
    }

   @Override
   public String renderResource(EmbeddedResource resource, RenderContext context) {
        String rendered = this.renderByConditionalRenderers(resource, context);
        if (rendered != null) {
            return rendered;
        }
        return super.renderResource(resource, context);
    }

    private String renderByConditionalRenderers(EmbeddedResource resource, RenderContext context) {
        for (ConditionalEmbeddedRenderer renderer : this.conditionalRenderers) {
            String rendered;
            if (!renderer.shouldRenderResource(resource, context) || !Objects.nonNull(rendered = renderer.renderResource(resource, context))) continue;
            return rendered;
        }
        return null;
    }
}
