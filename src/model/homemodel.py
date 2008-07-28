# Copyright (C) 2006-2007 Owen Williams.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging

import gobject
import wnck

from sugar import wm
from sugar import activity

from model.homeactivity import HomeActivity

class HomeModel(gobject.GObject):
    """Model of the "Home" view (activity management)
    
    The HomeModel is basically the point of registration
    for all running activities within Sugar.  It traps
    events that tell the system there is a new activity
    being created (generated by the activity factories),
    or removed, as well as those which tell us that the
    currently focussed activity has changed.
    
    The HomeModel tracks a set of HomeActivity instances,
    which are tracking the window to activity mappings
    the activity factories have set up.
    """
    __gsignals__ = {
        'activity-added':          (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT])),
        'activity-removed':        (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT])),
        'active-activity-changed': (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT])),
        'tabbing-activity-changed': (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT])),
        'launch-started':          (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT])),
        'launch-completed':        (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT])),
        'launch-failed':           (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE, 
                                   ([gobject.TYPE_PYOBJECT]))
    }
    
    def __init__(self):
        gobject.GObject.__init__(self)

        self._activities = []
        self._active_activity = None
        self._tabbing_activity = None

        screen = wnck.screen_get_default()
        screen.connect('window-opened', self._window_opened_cb)
        screen.connect('window-closed', self._window_closed_cb)
        screen.connect('active-window-changed',
                       self._active_window_changed_cb)

    def _get_activities_with_window(self):
        ret = []
        for i in self._activities:
            if i.get_window() is not None:
                ret.append(i)
        return ret

    def get_previous_activity(self, current=None):
        if not current:
            current = self._active_activity

        activities = self._get_activities_with_window()
        i = activities.index(current)
        if len(activities) == 0:
            return None
        elif i - 1 >= 0:
            return activities[i - 1]
        else:
            return activities[len(activities) - 1]

    def get_next_activity(self, current=None):
        if not current:
            current = self._active_activity

        activities = self._get_activities_with_window()
        i = activities.index(current)
        if len(activities) == 0:
            return None
        elif i + 1 < len(activities):
            return activities[i + 1]
        else:
            return activities[0]

    def get_active_activity(self):
        """Returns the activity that the user is currently working in"""
        return self._active_activity

    def get_tabbing_activity(self):
        """Returns the activity that is currently highlighted during tabbing"""
        return self._tabbing_activity

    def set_tabbing_activity(self, activity):
        """Sets the activity that is currently highlighted during tabbing"""
        self._tabbing_activity = activity
        self.emit("tabbing-activity-changed", self._tabbing_activity)

    def _set_active_activity(self, home_activity):
        if self._active_activity == home_activity:
            return

        if self._active_activity:
            service = self._active_activity.get_service()
            if service:
                service.SetActive(False,
                                  reply_handler=self._set_active_success,
                                  error_handler=self._set_active_error)
        if home_activity:
            service = home_activity.get_service()
            if service:
                service.SetActive(True,
                                  reply_handler=self._set_active_success,
                                  error_handler=self._set_active_error)

        self._active_activity = home_activity
        self.emit('active-activity-changed', self._active_activity)

    def __iter__(self): 
        return iter(self._activities)
        
    def __len__(self):
        return len(self._activities)
        
    def __getitem__(self, i):
        return self._activities[i]
        
    def index(self, obj):
        return self._activities.index(obj)
        
    def _window_opened_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_NORMAL:
            home_activity = None

            activity_id = wm.get_activity_id(window)

            service_name = wm.get_bundle_id(window)
            if service_name:
                registry = activity.get_registry()
                activity_info = registry.get_activity(service_name)
            else:
                activity_info = None

            if activity_id:
                home_activity = self._get_activity_by_id(activity_id)

            if not home_activity:
                home_activity = HomeActivity(activity_info, activity_id)
                self._add_activity(home_activity)

            home_activity.set_window(window)

            home_activity.props.launching = False
            self.emit('launch-completed', home_activity)

            if self._active_activity is None:
                self._set_active_activity(home_activity)

    def _window_closed_cb(self, screen, window):
        if window.get_window_type() == wnck.WINDOW_NORMAL:
            self._remove_activity_by_xid(window.get_xid())

    def _get_activity_by_xid(self, xid):
        for home_activity in self._activities:
            if home_activity.get_xid() == xid:
                return home_activity
        return None

    def _get_activity_by_id(self, activity_id):
        for home_activity in self._activities:
            if home_activity.get_activity_id() == activity_id:
                return home_activity
        return None

    def _set_active_success(self):
        pass
    
    def _set_active_error(self, err):
        logging.error("set_active() failed: %s" % err)

    def _active_window_changed_cb(self, screen, previous_window=None):
        window = screen.get_active_window()
        if window is None:
            return

        if window.get_window_type() != wnck.WINDOW_DIALOG:
            while window.get_transient() is not None:
                window = window.get_transient()

        act = self._get_activity_by_xid(window.get_xid())
        if act is not None:
            self._set_active_activity(act)

    def _add_activity(self, home_activity):
        self._activities.append(home_activity)
        self.emit('activity-added', home_activity)

    def _remove_activity(self, home_activity):
        if home_activity == self._active_activity:
            windows = wnck.screen_get_default().get_windows_stacked()
            windows.reverse()
            for window in windows:
                new_activity = self._get_activity_by_xid(window.get_xid())
                if new_activity is not None:
                    self._set_active_activity(new_activity)
                    break
            else:
                logging.error('No activities are running')
                self._set_active_activity(None)

        self.emit('activity-removed', home_activity)
        self._activities.remove(home_activity)

    def _remove_activity_by_xid(self, xid):
        home_activity = self._get_activity_by_xid(xid)
        if home_activity:
            self._remove_activity(home_activity)
        else:
            logging.error('Model for window %d does not exist.' % xid)

    def notify_launch(self, activity_id, service_name):
        registry = activity.get_registry()
        activity_info = registry.get_activity(service_name)
        if not activity_info:
            raise ValueError("Activity service name '%s'" \
                             " was not found in the bundle registry."
                             % service_name)
        home_activity = HomeActivity(activity_info, activity_id)
        home_activity.props.launching = True
        self._add_activity(home_activity)

        self._set_active_activity(home_activity)

        self.emit('launch-started', home_activity)

        # FIXME: better learn about finishing processes by receiving a signal.
        # Now just check whether an activity has a window after ~90sec
        gobject.timeout_add(90000, self._check_activity_launched, activity_id)

    def notify_launch_failed(self, activity_id):
        home_activity = self._get_activity_by_id(activity_id)
        if home_activity:
            logging.debug("Activity %s (%s) launch failed" % \
                          (activity_id, home_activity.get_type()))
            home_activity.props.launching = False
            self._remove_activity(home_activity)
        else:
            logging.error('Model for activity id %s does not exist.'
                          % activity_id)

        self.emit('launch-failed', home_activity)

    def _check_activity_launched(self, activity_id):
        home_activity = self._get_activity_by_id(activity_id)
        if home_activity and home_activity.props.launching:
            logging.debug('Activity %s still launching, assuming it failed...'
                          % activity_id)
            self.notify_launch_failed(activity_id)
        return False
