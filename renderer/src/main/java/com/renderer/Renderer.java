package com.renderer;

import com.atlassian.jira.JiraFeatureFlagRegistrar;
import com.atlassian.jira.component.ComponentAccessor;
import com.atlassian.jira.issue.fields.renderer.IssueRenderContext;
import com.atlassian.jira.issue.fields.renderer.wiki.TokenRendererAwareRendererComparator;
import com.atlassian.jira.plugin.renderercomponent.RendererComponentFactoryDescriptor;
import com.atlassian.jira.plugin.util.ModuleDescriptorComparator;
import com.atlassian.plugin.PluginAccessor;
import com.atlassian.renderer.*;
import com.atlassian.renderer.embedded.EmbeddedResourceRenderer;
import com.atlassian.renderer.links.LinkRenderer;
import com.atlassian.renderer.util.UnicodeEscapingTool;
import com.atlassian.renderer.v2.*;
import com.atlassian.renderer.v2.components.*;
import com.atlassian.renderer.v2.components.block.*;
import com.atlassian.renderer.v2.components.list.ListBlockRenderer;
import com.atlassian.renderer.v2.components.phrase.DashRendererComponent;
import com.atlassian.renderer.v2.components.phrase.ForceNewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.NewLineRendererComponent;
import com.atlassian.renderer.v2.components.phrase.PhraseRendererComponent;
import com.atlassian.renderer.v2.components.table.TableBlockRenderer;
import com.atlassian.renderer.v2.macro.DefaultMacroManager;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class Renderer {
   private final V2Renderer Renderer;
   private final V2RendererFacade Facade;

   public Renderer() {
      var components = new ArrayList<RendererComponent>();
      PluginAccessor pluginAccessor = (PluginAccessor) ComponentAccessor.getComponentOfType(PluginAccessor.class);
      ArrayList descriptors = new ArrayList(
            pluginAccessor.getEnabledModuleDescriptorsByClass(RendererComponentFactoryDescriptor.class));
      Collections.sort(descriptors, ModuleDescriptorComparator.COMPARATOR);
      for (RendererComponentFactoryDescriptor descriptor : descriptors) {
         PluggableRendererComponentFactory rendererComponentFactory = (PluggableRendererComponentFactory) descriptor
               .getModule();
         RendererComponent rendererComponent = rendererComponentFactory.getRendererComponent();
         components.add(rendererComponent);
      }
      Collections.sort(components, TokenRendererAwareRendererComparator.COMPARATOR);
      Renderer.setComponents(components);
      Facade = new V2RendererFacade(
            (RendererConfiguration) ComponentAccessor.getComponent(RendererConfiguration.class),
            (LinkRenderer) ComponentAccessor.getComponent(LinkRenderer.class),
            (EmbeddedResourceRenderer) ComponentAccessor.getComponent(EmbeddedResourceRenderer.class),
            Renderer,
            (UnicodeEscapingTool) ComponentAccessor.getComponent(UnicodeEscapingTool.class), true);
   }

   public String render(String text, IssueRenderContext context) {
      var renderContext = getRenderContext(context);
      return Facade.convertWikiToXHtml(renderContext, text);
   }

   private RenderContext getRenderContext(IssueRenderContext context) {
      RenderContext renderContext = new RenderContext();
      if (context != null) {
         renderContext.getParams().putAll(context.getParams());
         if (context.getIssue() != null) {
            renderContext.addParam("jira.issue", context.getIssue());
         }
      }
      renderContext.setBaseUrl("https://bugs.mojang.com");
      renderContext.pushRenderMode(RenderMode.ALL);
      renderContext.addParam("com.atlassian.renderer.v2.components.macro.render.consider.variable.format", true);
      return renderContext;
   }
}
