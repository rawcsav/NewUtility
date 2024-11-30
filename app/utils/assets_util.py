from flask_assets import Bundle


def compile_static_assets(assets):
    common_style_bundle = Bundle("src/css/*.css", filters="cssmin", output="dist/css/common.css")
    home_style_bundle = Bundle("home_bp/home.css", filters="cssmin", output="dist/css/home.css")
    auth_style_bundle = Bundle("auth_bp/auth.css", filters="cssmin", output="dist/css/auth.css")
    user_style_bundle = Bundle("user_bp/user.css", filters="cssmin", output="dist/css/user.css")
    chat_style_bundle = Bundle("chat_bp/*.css", filters="cssmin", output="dist/css/chat.css")
    embedding_style_bundle = Bundle("embedding_bp/embedding.css", filters="cssmin", output="dist/css/embedding.css")
    image_style_bundle = Bundle("image_bp/image.css", filters="cssmin", output="dist/css/image.css")
    audio_style_bundle = Bundle("audio_bp/audio.css", filters="cssmin", output="dist/css/audio.css")
    cwd_style_bundle = Bundle("cwd_bp/cwd.css", filters="cssmin", output="dist/css/cwd.css")

    # Register all the bundles

    assets.register("common_style_bundle", common_style_bundle)
    assets.register("home_style_bundle", home_style_bundle)
    assets.register("auth_style_bundle", auth_style_bundle)
    assets.register("user_style_bundle", user_style_bundle)
    assets.register("chat_style_bundle", chat_style_bundle)
    assets.register("embedding_style_bundle", embedding_style_bundle)
    assets.register("image_style_bundle", image_style_bundle)
    assets.register("audio_style_bundle", audio_style_bundle)
    assets.register("cwd_style_bundle", cwd_style_bundle)

    # JavaScript bundles
    # common_js_bundle = Bundle("src/js/*.js", filters="jsmin" if app.config['ENV'] == 'production' else None, output="dist/js/common.js")
    home_js_bundle = Bundle("home_bp/home.js", filters="jsmin", output="dist/js/home.js")
    auth_js_bundle = Bundle("auth_bp/auth.js", filters="jsmin", output="dist/js/auth.js")
    user_js_bundle = Bundle("user_bp/user.js", filters="jsmin", output="dist/js/user.js")
    chat_js_bundle = Bundle("chat_bp/chat.js", filters="jsmin", output="dist/js/chat.js")
    embedding_js_bundle = Bundle("embedding_bp/embedding.js", filters="jsmin", output="dist/js/embedding.js")
    image_js_bundle = Bundle("image_bp/image.js", filters="jsmin", output="dist/js/image.js")
    audio_js_bundle = Bundle("audio_bp/audio.js", filters="jsmin", output="dist/js/audio.js")
    cwd_js_bundle = Bundle("cwd_bp/cwd.js", filters="jsmin", output="dist/js/cwd.js")

    # Register JavaScript bundles
    # assets.register("common_js_bundle", common_js_bundle)
    assets.register("home_js_bundle", home_js_bundle)
    assets.register("user_js_bundle", user_js_bundle)
    assets.register("chat_js_bundle", chat_js_bundle)
    assets.register("auth_js_bundle", auth_js_bundle)
    assets.register("embedding_js_bundle", embedding_js_bundle)
    assets.register("image_js_bundle", image_js_bundle)
    assets.register("audio_js_bundle", audio_js_bundle)
    assets.register("cwd_js_bundle", cwd_js_bundle)

    if assets.config["FLASK_ENV"] == "development":
        common_style_bundle.build()
        home_style_bundle.build()
        auth_style_bundle.build()
        user_style_bundle.build()
        chat_style_bundle.build()
        embedding_style_bundle.build()
        image_style_bundle.build()
        audio_style_bundle.build()
        cwd_style_bundle.build()

        # common_js_bundle.build()
        home_js_bundle.build()
        auth_js_bundle.build()
        user_js_bundle.build()
        chat_js_bundle.build()
        embedding_js_bundle.build()
        image_js_bundle.build()
        audio_js_bundle.build()
        cwd_js_bundle.build()
    else:
        pass

    return assets
