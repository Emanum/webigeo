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

#include "IosScene.h"

#include <SDL2/SDL.h>
#include <SDL2/SDL_syswm.h>

#import <QuartzCore/CAMetalLayer.h>
#import <UIKit/UIKit.h>

#include <QDebug>

namespace webgpu_app::ios {

namespace {
    UIWindowScene* first_window_scene()
    {
        for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
            if ([scene isKindOfClass:[UIWindowScene class]])
                return (UIWindowScene*)scene;
        }
        return nil;
    }
} // namespace

void attach_window_to_scene(SDL_Window* window)
{
    SDL_SysWMinfo info;
    SDL_VERSION(&info.version);
    if (!SDL_GetWindowWMInfo(window, &info) || info.subsystem != SDL_SYSWM_UIKIT) {
        qWarning() << "attach_window_to_scene: no UIKit window";
        return;
    }

    // The scene connects asynchronously after launch; SDL_main may already be running.
    UIWindowScene* scene = first_window_scene();
    for (int i = 0; scene == nil && i < 500; i++) {
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.01, true);
        scene = first_window_scene();
    }
    if (scene == nil) {
        qWarning() << "attach_window_to_scene: no window scene connected after 5 s";
        return;
    }

    UIWindow* ui_window = info.info.uikit.window;
    ui_window.windowScene = scene;
    ui_window.frame = scene.coordinateSpace.bounds;
    [ui_window makeKeyAndVisible];
}

namespace {
    // The part of the window the app draws into: the safe area, i.e. clear of the Dynamic
    // Island, the top edge (status bar / notification gesture) and the home indicator. The UI
    // positions its windows at the screen edges, and the system takes touches there.
    CGRect content_rect(UIWindow* ui_window) { return UIEdgeInsetsInsetRect(ui_window.bounds, ui_window.safeAreaInsets); }
} // namespace

bool current_window_size(SDL_Window* window, int& width, int& height)
{
    SDL_SysWMinfo info;
    SDL_VERSION(&info.version);
    if (!SDL_GetWindowWMInfo(window, &info) || info.subsystem != SDL_SYSWM_UIKIT || info.info.uikit.window == nil)
        return false;
    const CGSize size = content_rect(info.info.uikit.window).size;
    width = int(size.width);
    height = int(size.height);
    return width > 0 && height > 0;
}

void fit_views_to_window(SDL_Window* window)
{
    SDL_SysWMinfo info;
    SDL_VERSION(&info.version);
    if (!SDL_GetWindowWMInfo(window, &info) || info.subsystem != SDL_SYSWM_UIKIT || info.info.uikit.window == nil)
        return;
    UIWindow* ui_window = info.info.uikit.window;
    UIView* root = ui_window.rootViewController.view;
    if (root == nil)
        return;
    // SDL's root view is also the view that receives touches, so insetting it keeps render and
    // touch coordinates consistent. The bars outside the safe area stay black.
    ui_window.backgroundColor = UIColor.blackColor;
    const CGRect frame = content_rect(ui_window);
    if (!CGRectEqualToRect(root.frame, frame))
        root.frame = frame;
    for (UIView* sub in root.subviews) {
        if ([sub.layer isKindOfClass:[CAMetalLayer class]] && !CGRectEqualToRect(sub.frame, root.bounds))
            sub.frame = root.bounds;
    }
}

} // namespace webgpu_app::ios
