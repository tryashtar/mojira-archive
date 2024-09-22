package com.renderer;

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

public class FakeUserManager implements UserManager {

   @Override
   public boolean canDirectoryUpdateUserPassword(Directory arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'canDirectoryUpdateUserPassword'");
   }

   @Override
   public boolean canRenameUser(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'canRenameUser'");
   }

   @Override
   public boolean canUpdateGroupMembershipForUser(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'canUpdateGroupMembershipForUser'");
   }

   @Override
   public boolean canUpdateUser(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'canUpdateUser'");
   }

   @Override
   public boolean canUpdateUserPassword(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'canUpdateUserPassword'");
   }

   @Override
   public ApplicationUser createUser(UserDetails arg0) throws CreateException, PermissionException {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'createUser'");
   }

   @Override
   public ApplicationUser findUserInDirectory(String arg0, Long arg1) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'findUserInDirectory'");
   }

   @Override
   public String generateRandomPassword() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'generateRandomPassword'");
   }

   @Override
   public Collection<ApplicationUser> getAllApplicationUsers() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAllApplicationUsers'");
   }

   @Override
   public Set<Group> getAllGroups() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAllGroups'");
   }

   @Override
   public Set<ApplicationUser> getAllUsers() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getAllUsers'");
   }

   @Override
   public Optional<Directory> getDefaultCreateDirectory() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getDefaultCreateDirectory'");
   }

   @Override
   public Directory getDirectory(Long arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getDirectory'");
   }

   @Override
   public Group getGroup(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getGroup'");
   }

   @Override
   public Group getGroupObject(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getGroupObject'");
   }

   @Override
   public Collection<Group> getGroups() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getGroups'");
   }

   @Override
   public int getTotalUserCount() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getTotalUserCount'");
   }

   @Override
   public ApplicationUser getUser(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUser'");
   }

   @Override
   public Optional<ApplicationUser> getUserById(Long arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserById'");
   }

   @Override
   public ApplicationUser getUserByKey(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserByKey'");
   }

   @Override
   public ApplicationUser getUserByKeyEvenWhenUnknown(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserByKeyEvenWhenUnknown'");
   }

   @Override
   public ApplicationUser getUserByName(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserByName'");
   }

   @Override
   public ApplicationUser getUserByNameEvenWhenUnknown(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserByNameEvenWhenUnknown'");
   }

   @Override
   public ApplicationUser getUserEvenWhenUnknown(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserEvenWhenUnknown'");
   }

   @Override
   public Optional<UserIdentity> getUserIdentityById(Long arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserIdentityById'");
   }

   @Override
   public Optional<UserIdentity> getUserIdentityByKey(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserIdentityByKey'");
   }

   @Override
   public Optional<UserIdentity> getUserIdentityByUsername(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserIdentityByUsername'");
   }

   @Override
   public ApplicationUser getUserObject(String arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserObject'");
   }

   @Override
   public UserState getUserState(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserState'");
   }

   @Override
   public UserState getUserState(String arg0, long arg1) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUserState'");
   }

   @Override
   public Collection<ApplicationUser> getUsers() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getUsers'");
   }

   @Override
   public List<Directory> getWritableDirectories() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'getWritableDirectories'");
   }

   @Override
   public boolean hasGroupWritableDirectory() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'hasGroupWritableDirectory'");
   }

   @Override
   public boolean hasPasswordWritableDirectory() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'hasPasswordWritableDirectory'");
   }

   @Override
   public boolean hasWritableDirectory() {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'hasWritableDirectory'");
   }

   @Override
   public boolean isUserExisting(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'isUserExisting'");
   }

   @Override
   public void updateUser(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'updateUser'");
   }

   @Override
   public boolean userCanUpdateOwnDetails(ApplicationUser arg0) {
      // TODO Auto-generated method stub
      throw new UnsupportedOperationException("Unimplemented method 'userCanUpdateOwnDetails'");
   }
   
}
