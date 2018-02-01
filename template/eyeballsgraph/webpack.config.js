const path = require("path");
const webpack = require("webpack");
const CopyWebpackPlugin = require("copy-webpack-plugin");

var dir_app = path.resolve(__dirname, "app");
var dir_build = path.resolve(__dirname, "build");
var dir_html = path.resolve(__dirname, "html");
var dir_data = path.resolve(__dirname, "data");

module.exports = {
  entry: ["babel-polyfill", path.resolve(dir_app, "index.js")],
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: [/node_modules/],
        include: [/app/],
        use: ["babel-loader"]
      },
      {
        test: /\.less$/,
        use: [
          { loader: "style-loader" },
          { loader: "css-loader" },
          { loader: "less-loader" }
        ]
      },
      {
        test: /\.css$/,
        use: [
          { loader: "style-loader" },
          { loader: "css-loader", options: { modules: true } }
        ]
      }
    ]
  },
  resolve: {
    extensions: ["*", ".js", ".jsx"]
  },
  output: {
    path: dir_build,
    publicPath: "/",
    filename: "bundle.js"
  },
  context: dir_app,
  devtool: "cheap-module-source-map",
  devServer: {
    contentBase: dir_build,
    historyApiFallback: {
      rewrites: [
        { from: /bundle\.js/, to: "/bundle.js" },
        { from: /index\.html/, to: "/index.html" },
        { from: /[a-zA-Z]{2}\/[0-9]{4}\/[0-9]{2}\/[0-9]{2}/, to: "/" },
        { from: /[a-zA-Z]{2}/, to: "/" }
      ]
    }
  },
  plugins: [
    new CopyWebpackPlugin([{ from: dir_html }, { from: dir_data }]),
    // enable HMR globally
    new webpack.HotModuleReplacementPlugin(),
    // prints more readable module names in the browser console on HMR updates
    new webpack.NamedModulesPlugin()
  ]
};
