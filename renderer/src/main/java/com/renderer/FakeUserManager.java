package com.renderer;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.Set;

import com.atlassian.crowd.embedded.api.Directory;
import com.atlassian.crowd.embedded.api.Group;
import com.atlassian.jira.exception.CreateException;
import com.atlassian.jira.exception.PermissionException;
import com.atlassian.jira.user.ApplicationUser;
import com.atlassian.jira.user.UserDetails;
import com.atlassian.jira.user.util.UserIdentity;
import com.atlassian.jira.user.util.UserManager;
import com.google.gson.JsonParser;

public class FakeUserManager implements UserManager {
   private final Path userFolder;

   public FakeUserManager(Path userFolder) {
      this.userFolder = userFolder;
   }

   public ApplicationUser getUserByName(String username) {
      String encoded;
      try {
         encoded = URLEncoder.encode(username, "UTF-8");
      }
      catch (UnsupportedEncodingException ex) {
         return null;
      }
      var path = userFolder.resolve(encoded + ".json");
      String json;
      try {
         json = Files.readString(path);
      } catch (IOException ex) {
         return null;
      }
      var data = new JsonParser().parse(json).getAsJsonObject();
      var name = data.get("name").getAsString();
      var display = data.get("displayName").getAsString();
      return new FakeUser(name, display);
   }

   public boolean canDirectoryUpdateUserPassword(Directory arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean canRenameUser(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean canUpdateGroupMembershipForUser(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean canUpdateUser(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean canUpdateUserPassword(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser createUser(UserDetails arg0) throws CreateException, PermissionException {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser findUserInDirectory(String arg0, Long arg1) {
      throw new UnsupportedOperationException();
   }

   public String generateRandomPassword() {
      throw new UnsupportedOperationException();
   }

   public Collection<ApplicationUser> getAllApplicationUsers() {
      throw new UnsupportedOperationException();
   }

   public Set<Group> getAllGroups() {
      throw new UnsupportedOperationException();
   }

   public Set<ApplicationUser> getAllUsers() {
      throw new UnsupportedOperationException();
   }

   public Optional<Directory> getDefaultCreateDirectory() {
      throw new UnsupportedOperationException();
   }

   public Directory getDirectory(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public Group getGroup(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Group getGroupObject(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Collection<Group> getGroups() {
      throw new UnsupportedOperationException();
   }

   public int getTotalUserCount() {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getUser(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Optional<ApplicationUser> getUserById(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getUserByKey(String arg0) {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getUserByKeyEvenWhenUnknown(String arg0) {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getUserObject(String arg0) {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getUserByNameEvenWhenUnknown(String arg0) {
      throw new UnsupportedOperationException();
   }

   public ApplicationUser getUserEvenWhenUnknown(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Optional<UserIdentity> getUserIdentityById(Long arg0) {
      throw new UnsupportedOperationException();
   }

   public Optional<UserIdentity> getUserIdentityByKey(String arg0) {
      throw new UnsupportedOperationException();
   }

   public Optional<UserIdentity> getUserIdentityByUsername(String arg0) {
      throw new UnsupportedOperationException();
   }

   public UserState getUserState(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public UserState getUserState(String arg0, long arg1) {
      throw new UnsupportedOperationException();
   }

   public Collection<ApplicationUser> getUsers() {
      throw new UnsupportedOperationException();
   }

   public List<Directory> getWritableDirectories() {
      throw new UnsupportedOperationException();
   }

   public boolean hasGroupWritableDirectory() {
      throw new UnsupportedOperationException();
   }

   public boolean hasPasswordWritableDirectory() {
      throw new UnsupportedOperationException();
   }

   public boolean hasWritableDirectory() {
      throw new UnsupportedOperationException();
   }

   public boolean isUserExisting(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public void updateUser(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

   public boolean userCanUpdateOwnDetails(ApplicationUser arg0) {
      throw new UnsupportedOperationException();
   }

}
