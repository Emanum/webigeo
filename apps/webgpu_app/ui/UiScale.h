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

namespace webgpu_app::ui {

// Scale of the ImGui layout relative to the desktop design (fonts, spacing, and the fixed pixel
// widths some panels use). A phone renders at its point size for now (440 wide on an iPhone 17
// Pro Max), where the desktop layout - 16 px fonts, a 430 px sidebar - covers the whole screen.
#ifdef ALP_PLATFORM_IOS
inline constexpr float UI_SCALE = 0.75f;
#else
inline constexpr float UI_SCALE = 1.0f;
#endif

} // namespace webgpu_app::ui
