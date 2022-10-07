from panda3d.core import loadPrcFileData

conf = """
win-size 1280 720
win-fixed-size 1
window-title Ghost Runner
show-frame-rate-meter 1
textures-power-2 none
#fullscreen true
"""

loadPrcFileData("", conf)

from panda3d.core import WindowProperties, \
    PointLight, \
    CollisionTraverser, CollisionHandlerQueue, CollisionNode, CollisionPolygon, \
    GeomVertexFormat, NodePath, Point3

from direct.showbase.ShowBase import ShowBase
import sys
import simplepbr

class Game(ShowBase):
    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.pipeline = simplepbr.init()

        self.map = self.loader.loadModel("assets/map.bam")
        self.map.reparentTo(self.render)
        self.showMesh(self.map)

        self.cTrav = CollisionTraverser()
        self.handler = CollisionHandlerQueue()
        self.cTrav.showCollisions(self.render)

        self.camera.setPos(0, 0, 3)
        self.camera.setP(-45)


        plight = PointLight("plight")
        plnp = self.render.attachNewNode(plight)
        plnp.setPos(5, -5, 8)
        self.render.setLight(plnp)


        # variables
        self.inGame = False
        self.isGameOver = False
        self.fullscreen = False
        self.lastMouseX, self.lastMouseY = None, None
        self.rotateH, self.rotateP = 0, 0
        self.pitchMax, self.pitchMin = 20, -60

        self.keyMap = {
            'a': False, 'd': False,
            'w': False, 's': False,
        }
        self.accept('a', self.setKey, ['a', True])
        self.accept('d', self.setKey, ['d', True])
        self.accept('w', self.setKey, ['w', True])
        self.accept('s', self.setKey, ['s', True])
        self.accept('a-up', self.setKey, ['a', False])
        self.accept('d-up', self.setKey, ['d', False])
        self.accept('w-up', self.setKey, ['w', False])
        self.accept('s-up', self.setKey, ['s', False])

        self.accept("f11", self.toggleFullscreen)
        self.accept("mouse1", self.mouseClick)
        self.accept("escape", sys.exit)

        self.taskMgr.add(self.update, "update")

    def update(self, task):
        dt = self.taskMgr.globalClock.getDt()

        if self.inGame:
            mw = self.mouseWatcherNode
            if mw.hasMouse():
                x, y = mw.getMouseX(), mw.getMouseY()
                if self.lastMouseX is not None:
                    dx, dy = x, y
                else:
                    dx, dy = 0, 0
                self.lastMouseX, self.lastMouseY = x, y
            else:
                self.toggleIngame()
                x, y, dx, dy = 0, 0, 0, 0
            self.recenterCursor()
            self.lastMouseX, self.lastMouseY = 0, 0
            
            self.rotateH -= dx * dt * 1500
            self.rotateP += dy * dt * 1000

            if self.rotateP > self.pitchMax:
                self.rotateP -= self.rotateP - self.pitchMax
            elif self.rotateP < self.pitchMin:
                self.rotateP -= self.rotateP - self.pitchMin

            self.camera.setH(self.rotateH)
            self.camera.setP(self.rotateP)
        
        if self.keyMap['a']:
            self.camera.setX(self.camera, -25 * dt)
        if self.keyMap['d']:
            self.camera.setX(self.camera, +25 * dt)
        if self.keyMap['w']:
            self.camera.setY(self.camera, +25 * dt)
        if self.keyMap['s']:
            self.camera.setY(self.camera, -25 * dt)
        self.camera.setZ(3)
        
        return task.cont
    
    # Records the state of the wasd keys
    def setKey(self, key, value):
        self.keyMap[key] = value
    
    # Toggles fullscreen
    def toggleFullscreen(self):
        self.fullscreen = not self.fullscreen

        wp = WindowProperties()
        wp.fullscreen = self.fullscreen
        if self.fullscreen:
            wp.size = (1920, 1080)
        else:
            wp.size = (1280, 720)
            wp.origin = (-2, -2)
            wp.fixed_size = True
        self.win.requestProperties(wp)


    # Toggles if player is in game
    def toggleIngame(self):
        if self.isGameOver:
            return
        self.inGame = not self.inGame

        wp = WindowProperties()
        wp.setCursorHidden(self.inGame)
        if self.inGame:
            wp.setMouseMode(WindowProperties.M_confined)
        else:
            wp.setMouseMode(WindowProperties.M_absolute)
        self.win.requestProperties(wp)
    

    # Recenters the cursor position
    def recenterCursor(self):
        self.win.movePointer(
            0,
            int(self.win.getProperties().getXSize() / 2),
            int(self.win.getProperties().getYSize() / 2)
        )
    
    # Method that gets called every time left mouse button is clicked
    def mouseClick(self):
        if self.inGame:
            pass
        else:
            self.toggleIngame()
    
    def showMesh(self, model):
        for node in model.findAllMatches("**/+CollisionNode"):
            parent = node.getParent()
            for geomNode in parent.findAllMatches('**/+GeomNode'):
                geomNode.reparent_to(parent)
    
    def createCollisionMesh(self, modelRoot):
        # create a temporary copy to generate the collision meshes from
        modelCopy = modelRoot.copyTo(self.render)
        modelCopy.detachNode()
        # "bake" the transformations into the vertices
        modelCopy.flattenLight()

        # create root node to attach collision nodes to
        collisionRoot = NodePath("collisionRoot")
        collisionRoot.reparentTo(modelRoot)
        # offset the collision meshes from the model so they're easier to see
        #collisionRoot.setX(1.)

        # create a collision mesh for each of the loaded models
        for model in modelCopy.findAllMatches("**/+GeomNode"):
            print(model)
            modelNode = model.node()
            print(modelNode.name)
            collisionNode = CollisionNode(modelNode.name)
            collisionMesh = collisionRoot.attachNewNode(collisionNode)
            collisionMesh.show()

            for geom in modelNode.modifyGeoms():
                geom.decomposeInPlace()
                vertexData = geom.modifyVertexData()
                vertexData.format = GeomVertexFormat.getV3()
                view = memoryview(vertexData.arrays[0]).cast("B").cast("f")
                indexList = geom.primitives[0].getVertexList()
                indexCount = len(indexList)

                for indices in (indexList[i:i+3] for i in range(0, indexCount, 3)):
                    points = [Point3(*view[index*3:index*3+3]) for index in indices]
                    collPoly = CollisionPolygon(*points)
                    collisionNode.addSolid(collPoly)

game = Game()
game.run()