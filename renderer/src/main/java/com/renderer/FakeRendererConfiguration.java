package com.renderer;

import com.atlassian.renderer.RendererConfiguration;

public class FakeRendererConfiguration implements RendererConfiguration {
   public String getCharacterEncoding() {
      return "UTF-8";
   }

   public String getWebAppContextPath() {
      return "";
   }

   public boolean isAllowCamelCase() {
      return false;
   }

   public boolean isNofollowExternalLinks() {
      return false;
   }

   public boolean isOpenExternalLinksInNewWindow() {
      return true;
   }
}