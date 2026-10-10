/*****************************************************************************
 * weBIGeo
 * Copyright (C) 2026 Manuel Eiweck
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *****************************************************************************/

#pragma once

struct SDL_Window;

namespace webgpu_app::ios {

/// Attaches the SDL window to the app's UIWindowScene and shows it.
///
/// Apps built with the iOS 26+ SDK must use the UIScene lifecycle. SDL2 creates its UIWindow
/// the pre-scene way, without a scene, and such a window is never displayed. Info.plist
/// declares one window scene; this hands SDL's window to it. Waits (pumping the run loop) for
/// the scene to connect, which UIKit does shortly after launch.
void attach_window_to_scene(SDL_Window* window);

/// Size of the SDL window's UIWindow in points, as UIKit lays it out right now. SDL's own cached
/// size can go stale: for a screenshot in landscape iOS briefly lays the app out in portrait,
/// and after returning SDL still reports the portrait size. Returns false if unavailable.
bool current_window_size(SDL_Window* window, int& width, int& height);

/// Keeps SDL's root view and its Metal view at the window's safe area. After a screenshot in
/// landscape (iOS lays the app out in portrait for the snapshot) UIKit does not lay SDL2's views
/// out again, so the Metal layer keeps the snapshot's portrait frame: half the screen stays
/// black, and after rotating back all of it. Cheap; only assigns frames that differ.
void fit_views_to_window(SDL_Window* window);

} // namespace webgpu_app::ios
