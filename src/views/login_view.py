import flet as ft

def login_button_style(fg_color, bg_color):
    return ft.ButtonStyle(
        color= fg_color,
        bgcolor= bg_color,
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=24,
        elevation={
            ft.ControlState.DEFAULT: 0,
            ft.ControlState.HOVERED: 5,
            ft.ControlState.PRESSED: 10,
        },
        animation_duration=500,
    )

def signup_button_style():
    return ft.ButtonStyle(
        color= "#fff0f3",
        bgcolor= "#ff88ac",
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=24,
        elevation={
            ft.ControlState.DEFAULT: 0,
            ft.ControlState.HOVERED: 5,
            ft.ControlState.PRESSED: 10,
        },
        animation_duration=500,
    )

def loginView(page):
    
    async def signup():
        page.views.pop()
        await page.push_route("/chat")


    button_fg_color = "#232d3b"
    button_bg_color = "#fffbfc"

    # --- Cabeçalho ---
    logo = ft.Container(
        content=ft.Icon(
            ft.Icons.FAVORITE, color=ft.Colors.RED, size=48
        ),
        padding=20,
        bgcolor="#ffe9ec",
        border_radius=20,
        shadow=[
            ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.WHITE_30,
                offset=ft.Offset(1, -4),
            ),
            ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.GREY_400,
                offset=ft.Offset(0, 3),
            ),
        ]
    )

    title = ft.Container(content=(
        ft.Text(
            "Match.AI", size=42
        )),
    )

    subtitle = ft.Container(content=
        ft.Row(
            controls=[
                ft.Text("Find your perfect match powered by advanced AI that understands who you truly are",
                        size=20,
                        text_align=ft.TextAlign.CENTER),
                ],
            wrap=True,
        )
    )

    # --- Instância dos botões ---
    google_login = ft.Button(
        content=ft.Text("Continue with Google",size=14),
        icon=ft.Image(src="assets/icons/google.svg",width=24,height=24),
        style=login_button_style(button_fg_color, button_bg_color),
        expand=True,
    )

    facebook_login = ft.Button(
        content=ft.Text("Continue with Facebook",size=14),
        icon=ft.Image(src="assets/icons/facebook.svg",width=24,height=24),
        style=login_button_style(button_fg_color, button_bg_color),
        expand=True,
    )

    apple_login = ft.Button(
        content=ft.Text("Continue with Apple",size=14),
        icon=ft.Image(src="assets/icons/apple.svg",width=24,height=24),
        style=login_button_style(button_fg_color, button_bg_color),
        expand=True,
    )

    signup_button = ft.Button(
        content=ft.Text("Start AI Interview", size=14),
        icon=ft.Icons.STAR,
        style=signup_button_style(),
        expand=True,
        on_click=signup,
    )

    terms_message= "By continuing, you agree to our Terms of Service and Privacy Policy"

    box = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(controls=[google_login],alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[facebook_login],alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[apple_login],alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[ft.Text("or", size=12)],alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[signup_button],alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(controls=[ft.Text(terms_message,size=12,text_align=ft.TextAlign.CENTER)],alignment=ft.MainAxisAlignment.CENTER,wrap=True),
            ],
            tight=True,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.Alignment.CENTER,
        ),
        margin=50,
        bgcolor=ft.Colors.WHITE_38,
        padding=18,
        border_radius=20,
    )

    one_column = ft.Column(
        controls=[
            logo,
            title,
            subtitle,
            box,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # --- Saída de View ---
    return ft.View(
        route="/login",
        controls=[
            one_column
        ],
        bgcolor=ft.Colors.PINK_50,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
    )